# Custom Cloud Build "builder" image that submits a compiled Vertex AI pipeline and waits for it.
# Adapted from DE2026 lab4/custom_cloud_build_builder_tools/pipeline_executor.
FROM python:3.12.7-slim
WORKDIR /usr/src/executor
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pipeline_executor.py .
ENTRYPOINT ["python3", "/usr/src/executor/pipeline_executor.py"]
