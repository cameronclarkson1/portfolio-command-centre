FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY api/ ./api/
COPY repo/ ./repo/

WORKDIR /app/api
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
