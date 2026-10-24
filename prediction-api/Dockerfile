# Prediction API image. Adapted from DE2026 lab2/prediction-api/Dockerfile.
FROM python:3.12.7-slim
WORKDIR /usr/src/myapp
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# model.pkl (and metadata.json) are copied into this folder by the deployment CI/CD pipeline
COPY . .
EXPOSE 5000
ENV MODEL_REPO=/usr/src/myapp
CMD ["python3", "app.py"]
