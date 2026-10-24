"""
Unit tests for the prediction API, run by the deployment CI/CD pipeline before the image is
built. In CI, testResources/model.pkl is first replaced with the newly published production
model, so these tests also check that the new model loads and answers in the expected format.
"""
import json
import os

import pytest

from app import app, predictor
from coffee_predictor import CoffeePredictor, InvalidInput

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(TEST_DIR, "../testResources/model.pkl")
REQUEST_FILE = os.path.join(TEST_DIR, "../testResources/prediction_request.json")


@pytest.fixture
def records():
    with open(REQUEST_FILE) as f:
        return json.load(f)


@pytest.fixture
def cp():
    p = CoffeePredictor()
    p.load_model(MODEL_FILE)
    return p


def test_predict_returns_one_result_per_record(cp, records):
    results = cp.predict(records)
    assert len(results) == len(records)
    for r in results:
        assert isinstance(r["liked"], bool)
        assert 0.0 <= r["probability"] <= 1.0


def test_model_is_sensible(cp, records):
    """Sanity check: a balanced chocolatey cup should score higher than a sour, thin, rubbery one."""
    good, bad = cp.predict(records)
    assert good["probability"] > bad["probability"]


def test_missing_field_is_rejected(cp, records):
    del records[0]["bitter"]
    with pytest.raises(InvalidInput):
        cp.predict(records)


def test_out_of_range_value_is_rejected(cp, records):
    records[0]["acidity"] = 9
    with pytest.raises(InvalidInput):
        cp.predict(records)


def test_http_endpoint(records):
    predictor.load_model(MODEL_FILE)
    client = app.test_client()
    ok = client.post("/coffee_predictor/", json=records)
    assert ok.status_code == 200 and len(ok.get_json()) == 2
    bad = client.post("/coffee_predictor/", json=[{"acidity": 3}])
    assert bad.status_code == 400
