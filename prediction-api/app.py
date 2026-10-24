"""REST API that serves the coffee-liking model. Adapted from DE2026 lab2/prediction-api."""
import os

from flask import Flask, jsonify, request

from coffee_predictor import CoffeePredictor, InvalidInput

app = Flask(__name__)
predictor = CoffeePredictor()


@app.route("/coffee_predictor/", methods=["POST"])
def predict():
    """Body: a JSON list of tasting records. Returns a list of predictions in the same order."""
    try:
        return jsonify(predictor.predict(request.get_json(force=True))), 200
    except InvalidInput as e:
        return jsonify(error=str(e)), 400


@app.route("/health", methods=["GET"])
def health():
    """Shows which model version is being served (useful to check a redeployment worked)."""
    predictor._ensure_model()
    return jsonify(status="ok", model=predictor.model_info), 200


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)), host="0.0.0.0")
