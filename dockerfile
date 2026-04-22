FROM python:3.13-slim
RUN pip install pytest pytest-html
WORKDIR /app