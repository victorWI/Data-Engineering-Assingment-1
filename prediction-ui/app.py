"""
Web UI for the coffee-liking predictor. Sends the form to the prediction API and shows the result.
Adapted from DE2026 lab2/prediction-ui (Dr. Indika Kumara).
"""
import os

import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# key, label, the five answer options (used for screen readers), and the two end words shown on the scale
JAR_QUESTIONS = [
    ("temperature", "Temperature", ["Much too cold", "Too cold", "Just right", "Too hot", "Much too hot"], "cold", "hot"),
    ("flavor_intensity", "Strength", ["Far too weak", "Too weak", "Just right", "Too strong", "Far too strong"], "weak", "strong"),
    ("acidity", "Acidity", ["Far too little", "Too little", "Just right", "Too much", "Far too much"], "flat", "sharp"),
    ("mouthfeel", "Body", ["Much too thin", "Too thin", "Just right", "Too thick", "Much too thick"], "thin", "thick"),
]
FLAVOURS = [
    ("tea_floral", "Tea / floral"), ("fruit", "Fruity"), ("citrus", "Citrus"), ("green_veg", "Green / vegetal"),
    ("paper_wood", "Papery / woody"), ("burnt", "Burnt"), ("cereal", "Cereal"), ("nutty", "Nutty"),
    ("dark_chocolate", "Dark chocolate"), ("caramel", "Caramel"), ("bitter", "Bitter"),
    ("astringent", "Astringent / drying"), ("roasted", "Roasted"), ("sour", "Sour"),
    ("thick_viscous", "Thick / syrupy"), ("sweet", "Sweet"), ("rubber", "Rubbery"),
]


# The model's probability is turned into one of three verdicts. About 61% of all cups in the
# study were liked, so probabilities close to that carry little information: in that middle band
# the UI says "Hard to say" instead of overstating a borderline prediction.
LIKE_THRESHOLD = 0.65
DISLIKE_THRESHOLD = 0.40


def verdict_for(probability):
    if probability >= LIKE_THRESHOLD:
        return "like"
    if probability < DISLIKE_THRESHOLD:
        return "dislike"
    return "unsure"


def form_to_record(form):
    record = {q[0]: int(form.get(q[0], 3)) for q in JAR_QUESTIONS}
    record.update({key: 1 if form.get(key) else 0 for key, _ in FLAVOURS})
    return record


@app.route("/", methods=["GET"])
@app.route("/checkcoffee", methods=["GET", "POST"])
def check_coffee():
    if request.method == "GET":
        return render_template("index.html", jar=JAR_QUESTIONS, flavours=FLAVOURS, selected=None, result=None)

    record = form_to_record(request.form)
    app.logger.info("Prediction input: %s", record)
    try:
        # PREDICTOR_API is set by the deployment CI/CD pipeline to the Cloud Run URL of the API
        res = requests.post(os.environ["PREDICTOR_API"], json=[record], timeout=30)
        res.raise_for_status()
        result, error = res.json()[0], None
        result["verdict"] = verdict_for(result["probability"])
    except Exception as e:  # show a friendly message instead of a server error
        app.logger.exception("Prediction API call failed")
        result, error = None, f"The prediction service could not be reached ({type(e).__name__})."
    return render_template("index.html", jar=JAR_QUESTIONS, flavours=FLAVOURS,
                           selected=record, result=result, error=error)


if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)), host="0.0.0.0")
