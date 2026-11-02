FROM python:3.12-slim
WORKDIR /suite
COPY . /suite
# Optional boto3 for Bedrock Converse judge; no app credentials baked into image.
RUN pip install --no-cache-dir "boto3>=1.35,<2"
CMD ["python","tools/validate_suite.py"]
