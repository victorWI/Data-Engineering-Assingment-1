"""
Continuous-training pipeline for the "Will I like this coffee?" predictor.

Built with the Kubeflow Pipelines (KFP v2) SDK and executed on Google Vertex AI Pipelines.
Structure adapted from the DE2026 course labs (lab4/ml-pipeline/dt_lr_train_pipeline.py,
Dr. Indika Kumara). Data: Cotter, Ristenpart & Guinard (2022), "Consumer preference data
for black coffee", Dryad, https://doi.org/10.25338/B8993H (CC0).

Pipeline steps
--------------
1. download_data          : copy the training CSV from the data bucket
2. validate_data          : schema / range checks, rename columns, create the label
3. split_data             : hold out 20% of the *consumers* (judges) as a test set
4. train_lr / train_rf    : train two candidate models in parallel, scored by grouped CV
5. select_best_model      : keep the candidate with the best cross-validated accuracy
6. evaluate_vs_champion   : compare the new model (challenger) with the model that is
                            currently in production (champion) on the same test set
7. deploy_model           : only if the challenger wins, publish it to
                            gs://<model_repo>/production/model.pkl
                            (this upload triggers the model-deployment CI/CD pipeline)

Running this file compiles the pipeline into a YAML definition:
    python coffee_training_pipeline.py --target_file coffee_training_pipeline.yaml
"""
import argparse
from typing import NamedTuple

from kfp import compiler, dsl
from kfp.dsl import Dataset, Input, Metrics, Model, Output

# Pinned so that the model pickled by the pipeline can be loaded by the prediction API
# (which pins the same versions in prediction-api/requirements.txt).
BASE_IMAGE = "python:3.12.7-slim"
SKLEARN = "scikit-learn==1.5.2"
PANDAS = "pandas==2.2.3"
GCS = "google-cloud-storage==2.18.2"


# --------------------------------------------------------------------------------------
# 1. Data ingestion
# --------------------------------------------------------------------------------------
@dsl.component(base_image=BASE_IMAGE, packages_to_install=[GCS])
def download_data(project_id: str, data_bucket: str, file_name: str, raw_data: Output[Dataset]):
    """Download the training data file from a Cloud Storage bucket."""
    import logging
    import sys

    from google.cloud import storage

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    client = storage.Client(project=project_id)
    client.bucket(data_bucket).blob(file_name).download_to_filename(raw_data.path + ".csv")
    logging.info("Downloaded gs://%s/%s", data_bucket, file_name)


# --------------------------------------------------------------------------------------
# 2. Data validation and preparation
# --------------------------------------------------------------------------------------
@dsl.component(base_image=BASE_IMAGE, packages_to_install=[PANDAS])
def validate_data(raw_data: Input[Dataset], clean_data: Output[Dataset]) -> NamedTuple(
        "outputs", [("rows", int), ("consumers", int), ("liked_share", float)]):
    """Check the schema and value ranges, then keep only the model inputs and the label.

    The pipeline fails here (instead of training on bad data) if a column is missing or
    a value is outside its documented range.
    """
    import logging
    import sys
    from collections import namedtuple

    import pandas as pd

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    df = pd.read_csv(raw_data.path + ".csv")
    logging.info("Raw data shape: %s", df.shape)

    # Just-about-right (JAR) ratings, 1 = much too little ... 3 = just right ... 5 = much too much
    jar = {"Temp": "temperature", "Flavor.intensity": "flavor_intensity",
           "Acidity": "acidity", "Mouthfeel": "mouthfeel"}
    # Check-all-that-apply (CATA) flavour notes, 0 = not noticed, 1 = noticed
    cata = {"Tea.floral": "tea_floral", "Fruit": "fruit", "Citrus": "citrus",
            "Green.veg": "green_veg", "Paper.wood": "paper_wood", "Burnt": "burnt",
            "Cereal": "cereal", "Nutty": "nutty", "Dark.chocolate": "dark_chocolate",
            "Caramel": "caramel", "Bitter": "bitter", "Astringent": "astringent",
            "Roasted": "roasted", "Sour": "sour", "Thick.viscous": "thick_viscous",
            "Sweet": "sweet", "Rubber": "rubber"}
    required = ["Judge", "Liking"] + list(jar) + list(cata)

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Schema check failed, missing columns: {missing}")

    before = len(df)
    df = df[required].dropna()
    logging.info("Dropped %d rows with missing values", before - len(df))

    checks = {"Liking": (1, 9), **{c: (1, 5) for c in jar}, **{c: (0, 1) for c in cata}}
    for col, (lo, hi) in checks.items():
        bad = ~df[col].between(lo, hi)
        if bad.any():
            raise ValueError(f"Range check failed for {col}: {int(bad.sum())} values outside [{lo}, {hi}]")
    if len(df) < 200:
        raise ValueError(f"Not enough data to train: {len(df)} rows")

    df = df.rename(columns={**jar, **cata, "Judge": "judge"})
    # Label: a liking score of 6 or more on the 9-point hedonic scale counts as "liked"
    # (same threshold as Gunning et al., 2026, npj Science of Food).
    df["liked"] = (df["Liking"] >= 6).astype(int)
    df = df.drop(columns=["Liking"])
    df.to_csv(clean_data.path + ".csv", index=False)

    result = namedtuple("outputs", ["rows", "consumers", "liked_share"])
    stats = result(len(df), int(df["judge"].nunique()), round(float(df["liked"].mean()), 4))
    logging.info("Validated data: %s", stats)
    return stats


# --------------------------------------------------------------------------------------
# 3. Train / test split by consumer
# --------------------------------------------------------------------------------------
@dsl.component(base_image=BASE_IMAGE, packages_to_install=[PANDAS, SKLEARN])
def split_data(clean_data: Input[Dataset], test_size: float,
               train_data: Output[Dataset], test_data: Output[Dataset]):
    """Hold out a fixed group of consumers as the test set.

    Every consumer tasted many coffees, so a random row split would put the same person in
    both train and test and overestimate accuracy. GroupShuffleSplit with a fixed seed keeps
    whole consumers together and picks the same test consumers on every run, so a new model
    and the production model are always compared on people neither of them was trained on.
    """
    import logging
    import sys

    import pandas as pd
    from sklearn.model_selection import GroupShuffleSplit

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    df = pd.read_csv(clean_data.path + ".csv")
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=42)
    train_idx, test_idx = next(splitter.split(df, groups=df["judge"]))
    df.iloc[train_idx].to_csv(train_data.path + ".csv", index=False)
    df.iloc[test_idx].to_csv(test_data.path + ".csv", index=False)
    logging.info("Train rows: %d, test rows: %d", len(train_idx), len(test_idx))


# --------------------------------------------------------------------------------------
# 4. Candidate models (run in parallel)
# --------------------------------------------------------------------------------------
@dsl.component(base_image=BASE_IMAGE, packages_to_install=[PANDAS, SKLEARN])
def train_lr(train_data: Input[Dataset], model: Output[Model]) -> float:
    """Train a logistic regression; return its 5-fold grouped cross-validation accuracy."""
    import logging
    import pickle
    import sys

    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold, cross_val_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    df = pd.read_csv(train_data.path + ".csv")
    X, y, groups = df.drop(columns=["judge", "liked"]), df["liked"], df["judge"]

    clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    cv_acc = float(cross_val_score(clf, X, y, cv=GroupKFold(n_splits=5), groups=groups).mean())
    clf.fit(X, y)

    with open(model.path + ".pkl", "wb") as f:
        pickle.dump(clf, f)
    model.metadata.update({"algo": "logistic_regression", "cv_accuracy": round(cv_acc, 4)})
    logging.info("LR cross-validated accuracy: %.4f", cv_acc)
    return cv_acc


@dsl.component(base_image=BASE_IMAGE, packages_to_install=[PANDAS, SKLEARN])
def train_rf(train_data: Input[Dataset], model: Output[Model]) -> float:
    """Train a random forest; return its 5-fold grouped cross-validation accuracy."""
    import logging
    import pickle
    import sys

    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import GroupKFold, cross_val_score

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    df = pd.read_csv(train_data.path + ".csv")
    X, y, groups = df.drop(columns=["judge", "liked"]), df["liked"], df["judge"]

    clf = RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=42, n_jobs=-1)
    cv_acc = float(cross_val_score(clf, X, y, cv=GroupKFold(n_splits=5), groups=groups).mean())
    clf.fit(X, y)

    with open(model.path + ".pkl", "wb") as f:
        pickle.dump(clf, f)
    model.metadata.update({"algo": "random_forest", "cv_accuracy": round(cv_acc, 4)})
    logging.info("RF cross-validated accuracy: %.4f", cv_acc)
    return cv_acc


# --------------------------------------------------------------------------------------
# 5. Algorithm selection
# --------------------------------------------------------------------------------------
@dsl.component(base_image=BASE_IMAGE)
def select_best_model(lr_model: Input[Model], lr_cv_accuracy: float,
                      rf_model: Input[Model], rf_cv_accuracy: float,
                      best_model: Output[Model]) -> str:
    """Copy the candidate with the higher cross-validated accuracy to `best_model`."""
    import logging
    import shutil
    import sys

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    winner = rf_model if rf_cv_accuracy > lr_cv_accuracy else lr_model
    shutil.copy(winner.path + ".pkl", best_model.path + ".pkl")
    best_model.metadata.update(winner.metadata)
    logging.info("LR cv=%.4f, RF cv=%.4f -> selected %s",
                 lr_cv_accuracy, rf_cv_accuracy, winner.metadata["algo"])
    return winner.metadata["algo"]


# --------------------------------------------------------------------------------------
# 6. Champion / challenger comparison
# --------------------------------------------------------------------------------------
@dsl.component(base_image=BASE_IMAGE, packages_to_install=[PANDAS, SKLEARN, GCS])
def evaluate_vs_champion(project_id: str, model_repo: str, min_improvement: float,
                         challenger: Input[Model], test_data: Input[Dataset],
                         metrics: Output[Metrics]) -> NamedTuple(
        "outputs", [("decision", str), ("challenger_accuracy", float), ("champion_accuracy", float)]):
    """Score the new model and the production model on the same held-out consumers.

    decision = "DEPLOY" if there is no production model yet, or if the challenger beats
    the champion by more than `min_improvement`; otherwise "KEEP".
    """
    import logging
    import pickle
    import sys
    from collections import namedtuple

    import pandas as pd
    from google.cloud import storage
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    df = pd.read_csv(test_data.path + ".csv")
    X, y = df.drop(columns=["judge", "liked"]), df["liked"]

    with open(challenger.path + ".pkl", "rb") as f:
        new_model = pickle.load(f)
    new_acc = float(accuracy_score(y, new_model.predict(X)))
    metrics.metadata["challenger_algo"] = challenger.metadata["algo"]
    metrics.log_metric("challenger_accuracy", round(new_acc, 4))
    metrics.log_metric("challenger_f1", round(float(f1_score(y, new_model.predict(X))), 4))
    metrics.log_metric("challenger_roc_auc", round(float(roc_auc_score(y, new_model.predict_proba(X)[:, 1])), 4))

    blob = storage.Client(project=project_id).bucket(model_repo).blob("production/model.pkl")
    if not blob.exists():
        logging.info("No production model found: deploying the first model")
        champ_acc, decision = -1.0, "DEPLOY"
    else:
        blob.download_to_filename("/tmp/champion.pkl")
        with open("/tmp/champion.pkl", "rb") as f:
            champion = pickle.load(f)
        champ_acc = float(accuracy_score(y, champion.predict(X)))
        decision = "DEPLOY" if new_acc > champ_acc + min_improvement else "KEEP"
    metrics.log_metric("champion_accuracy", round(champ_acc, 4))  # -1 means "no champion yet"
    metrics.log_metric("promoted", 1.0 if decision == "DEPLOY" else 0.0)
    logging.info("Challenger %.4f vs champion %.4f -> %s", new_acc, champ_acc, decision)

    result = namedtuple("outputs", ["decision", "challenger_accuracy", "champion_accuracy"])
    return result(decision, new_acc, champ_acc)


# --------------------------------------------------------------------------------------
# 7. Publish the model (only runs when the decision is DEPLOY)
# --------------------------------------------------------------------------------------
@dsl.component(base_image=BASE_IMAGE, packages_to_install=[GCS])
def deploy_model(project_id: str, model_repo: str, model: Input[Model], test_accuracy: float):
    """Archive the model under a timestamped name and publish it as the production model.

    The archive copy keeps every promoted version so an older model can be restored.
    production/model.pkl is uploaded last because its arrival triggers the deployment CI/CD.
    """
    import datetime
    import json
    import logging
    import sys

    from google.cloud import storage

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    bucket = storage.Client(project=project_id).bucket(model_repo)
    version = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    info = {"version": version, "algo": model.metadata["algo"],
            "cv_accuracy": model.metadata.get("cv_accuracy"),
            "test_accuracy": round(test_accuracy, 4)}

    bucket.blob(f"archive/{version}_{info['algo']}.pkl").upload_from_filename(model.path + ".pkl")
    bucket.blob("production/metadata.json").upload_from_string(json.dumps(info), "application/json")
    bucket.blob("production/model.pkl").upload_from_filename(model.path + ".pkl")
    logging.info("Published model version %s to gs://%s/production/", version, model_repo)


# --------------------------------------------------------------------------------------
# Pipeline definition
# --------------------------------------------------------------------------------------
@dsl.pipeline(name="coffee-liking-training-pipeline",
              description="Train, compare and publish the 'Will I like this coffee?' model")
def coffee_pipeline(project_id: str, data_bucket: str, trainset_filename: str, model_repo: str,
                    test_size: float = 0.2, min_improvement: float = 0.0):
    raw = download_data(project_id=project_id, data_bucket=data_bucket, file_name=trainset_filename)
    clean = validate_data(raw_data=raw.outputs["raw_data"])
    split = split_data(clean_data=clean.outputs["clean_data"], test_size=test_size)

    lr = train_lr(train_data=split.outputs["train_data"])
    rf = train_rf(train_data=split.outputs["train_data"])

    best = select_best_model(lr_model=lr.outputs["model"], lr_cv_accuracy=lr.outputs["Output"],
                             rf_model=rf.outputs["model"], rf_cv_accuracy=rf.outputs["Output"])

    evaluation = evaluate_vs_champion(project_id=project_id, model_repo=model_repo,
                                      min_improvement=min_improvement,
                                      challenger=best.outputs["best_model"],
                                      test_data=split.outputs["test_data"])

    with dsl.If(evaluation.outputs["decision"] == "DEPLOY", name="challenger-wins"):
        deploy_model(project_id=project_id, model_repo=model_repo,
                     model=best.outputs["best_model"],
                     test_accuracy=evaluation.outputs["challenger_accuracy"])


def compile_pipeline(target_file: str):
    compiler.Compiler().compile(pipeline_func=coffee_pipeline, package_path=target_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_file", default="coffee_training_pipeline.yaml")
    compile_pipeline(**vars(parser.parse_args()))
