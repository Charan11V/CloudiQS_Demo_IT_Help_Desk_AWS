FROM python:3.12-slim
WORKDIR /app
COPY mock_api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt pytest httpx
COPY mock_api /app/mock_api
COPY data /app/data
COPY tests /app/tests
EXPOSE 8000
CMD ["uvicorn", "mock_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
