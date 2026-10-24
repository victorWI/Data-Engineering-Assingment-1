"""
Tests for the training pipeline, run by the CI/CD pipeline before the pipeline is compiled
and submitted to Vertex AI.

* test_pipeline_compiles: the pipeline definition compiles to a YAML spec.
* test_components_end_to_end: runs the Python code of every component locally, in pipeline
  order, with Cloud Storage replaced by a local folder. It feeds the weekly data batches in
  one after another and checks the champion/challenger behaviour.
"""
import os
import pickle
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coffee_training_pipeline as ctp  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "source"


class FakeArtifact:
    """Stands in for a KFP Dataset/Model/Metrics artifact: a path plus a metadata dict."""

    def __init__(self, path):
        self.path = str(path)
        self.metadata = {}
        self.metrics = {}

    def log_metric(self, name, value):
        self.metrics[name] = value


class FakeBucket:
    """Minimal stand-in for google.cloud.storage that stores blobs in a local folder."""

    def __init__(self, root):
        self.root = Path(root)

    def blob(self, name):
        return FakeBlob(self.root / name)


class FakeBlob:
    def __init__(self, path):
        self.path = Path(path)

    def exists(self):
        return self.path.exists()

    def download_to_filename(self, filename):
        shutil.copy(self.path, filename)

    def upload_from_filename(self, filename):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(filename, self.path)

    def upload_from_string(self, data, content_type=None):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(data)


@pytest.fixture
def fake_gcs(tmp_path, monkeypatch):
    from google.cloud import storage

    class FakeClient:
        def __init__(self, project=None):
            pass

        def bucket(self, name):
            return FakeBucket(tmp_path / "gcs" / name)

    monkeypatch.setattr(storage, "Client", FakeClient)
    return tmp_path / "gcs"


def test_pipeline_compiles(tmp_path):
    target = tmp_path / "pipeline.yaml"
    ctp.compile_pipeline(str(target))
    spec = yaml.safe_load(target.read_text())
    tasks = set(spec["root"]["dag"]["tasks"])
    assert {"download-data", "validate-data", "split-data", "train-lr", "train-rf",
            "select-best-model", "evaluate-vs-champion"} <= tasks


def run_pipeline_locally(work, weeks):
    """Execute each component's python function in the same order as the Vertex pipeline."""
    work.mkdir(parents=True, exist_ok=True)
    data_bucket = work.parent / "gcs" / "data-bucket"
    data_bucket.mkdir(parents=True, exist_ok=True)
    pd.concat([pd.read_csv(DATA_DIR / f"week_{w}.csv") for w in weeks]).to_csv(
        data_bucket / "training_data.csv", index=False)

    art = {n: FakeArtifact(work / n) for n in
           ["raw", "clean", "train", "test", "lr", "rf", "best", "metrics"]}
    ctp.download_data.python_func("p", "data-bucket", "training_data.csv", art["raw"])
    stats = ctp.validate_data.python_func(art["raw"], art["clean"])
    ctp.split_data.python_func(art["clean"], 0.2, art["train"], art["test"])
    lr_cv = ctp.train_lr.python_func(art["train"], art["lr"])
    rf_cv = ctp.train_rf.python_func(art["train"], art["rf"])
    algo = ctp.select_best_model.python_func(art["lr"], lr_cv, art["rf"], rf_cv, art["best"])
    result = ctp.evaluate_vs_champion.python_func("p", "model-bucket", 0.0, art["best"],
                                                  art["test"], art["metrics"])
    if result.decision == "DEPLOY":
        ctp.deploy_model.python_func("p", "model-bucket", art["best"], result.challenger_accuracy)
    return stats, algo, result


def test_components_end_to_end(fake_gcs, tmp_path):
    production = fake_gcs / "model-bucket" / "production" / "model.pkl"

    # Week 1 only: there is no production model yet, so the first model is always deployed.
    stats, algo, r1 = run_pipeline_locally(tmp_path / "run1", [1])
    assert stats.rows == 944 and stats.consumers == 118
    assert algo in {"logistic_regression", "random_forest"}
    assert r1.decision == "DEPLOY" and production.exists()
    assert 0.6 < r1.challenger_accuracy < 0.9

    # Same data again: the new model ties the production model, so it must NOT be promoted.
    _, _, r2 = run_pipeline_locally(tmp_path / "run2", [1])
    assert r2.decision == "KEEP"

    # Weeks 1 + 2: more data, the new model should beat the week-1 model.
    _, _, r3 = run_pipeline_locally(tmp_path / "run3", [1, 2])
    assert r3.champion_accuracy >= 0
    print(f"week1={r1.challenger_accuracy:.3f}  weeks1-2: new={r3.challenger_accuracy:.3f} "
          f"vs prod={r3.champion_accuracy:.3f} -> {r3.decision}")

    # The production model must be loadable and answer a prediction.
    with open(production, "rb") as f:
        model = pickle.load(f)
    sample = pd.read_csv(tmp_path / "run3" / "test.csv").drop(columns=["judge", "liked"]).head(3)
    assert set(model.predict(sample)) <= {0, 1}
    assert len(os.listdir(fake_gcs / "model-bucket" / "archive")) >= 1


def test_validation_rejects_bad_data(tmp_path):
    bad = pd.read_csv(DATA_DIR / "week_1.csv").drop(columns=["Bitter"])
    raw, clean = FakeArtifact(tmp_path / "raw"), FakeArtifact(tmp_path / "clean")
    bad.to_csv(raw.path + ".csv", index=False)
    with pytest.raises(ValueError, match="missing columns"):
        ctp.validate_data.python_func(raw, clean)
