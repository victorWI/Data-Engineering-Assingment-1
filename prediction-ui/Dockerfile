# Prediction UI image. Adapted from DE2026 lab2/prediction-ui/Dockerfile.
FROM python:3.12.7-slim
WORKDIR /usr/src/myapp
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
# Overridden at deploy time with the real Cloud Run URL of the prediction API
ENV PREDICTOR_API=http://localhost:5001/coffee_predictor/
CMD ["python3", "app.py"]
