"""
Loads the trained model and turns a tasting description into a liked / not-liked prediction.
Structure adapted from DE2026 lab2/prediction-api (diabetes_predictor.py, Dr. Indika Kumara).
"""
import json
import logging
import os
import pickle

import pandas as pd

# The 21 model inputs. Order is taken from the trained model itself when available.
JAR_FEATURES = ["temperature", "flavor_intensity", "acidity", "mouthfeel"]  # 1..5, 3 = just right
FLAVOUR_FEATURES = ["tea_floral", "fruit", "citrus", "green_veg", "paper_wood", "burnt", "cereal",
                    "nutty", "dark_chocolate", "caramel", "bitter", "astringent", "roasted", "sour",
                    "thick_viscous", "sweet", "rubber"]  # 0 = not noticed, 1 = noticed
FEATURES = JAR_FEATURES + FLAVOUR_FEATURES


class InvalidInput(ValueError):
    """Raised when a prediction request is missing fields or has out-of-range values."""


class CoffeePredictor:
    def __init__(self):
        self.model = None
        self.model_info = {}

    def load_model(self, file_path):
        with open(file_path, "rb") as f:
            self.model = pickle.load(f)
        # metadata.json (version, algorithm, accuracy) is written next to the model by the pipeline
        meta_path = os.path.join(os.path.dirname(os.path.abspath(file_path)), "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                self.model_info = json.load(f)
        logging.info("Loaded model from %s %s", file_path, self.model_info)

    def _ensure_model(self):
        if self.model is None:
            model_repo = os.environ.get("MODEL_REPO", ".")
            self.load_model(os.path.join(model_repo, "model.pkl"))

    @staticmethod
    def _validate(records):
        if not isinstance(records, list) or not records:
            raise InvalidInput("Send a JSON list with at least one tasting record")
        for i, rec in enumerate(records):
            missing = [f for f in FEATURES if f not in rec]
            if missing:
                raise InvalidInput(f"Record {i} is missing fields: {missing}")
            for f in JAR_FEATURES:
                if not 1 <= float(rec[f]) <= 5:
                    raise InvalidInput(f"Record {i}: {f} must be between 1 and 5")
            for f in FLAVOUR_FEATURES:
                if int(rec[f]) not in (0, 1):
                    raise InvalidInput(f"Record {i}: {f} must be 0 or 1")

    def predict(self, records):
        """Return one {"liked": bool, "probability": float} per input record."""
        self._ensure_model()
        self._validate(records)
        columns = list(getattr(self.model, "feature_names_in_", FEATURES))
        X = pd.DataFrame(records)[columns].astype(float)
        probabilities = self.model.predict_proba(X)[:, 1]
        return [{"liked": bool(p >= 0.5), "probability": round(float(p), 3)} for p in probabilities]
