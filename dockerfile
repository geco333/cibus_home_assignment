FROM python:latest

ENV PORT=8000
EXPOSE ${PORT}
WORKDIR app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic ./alembic
COPY alembic.ini .
RUN alembic upgrade head

COPY schemas ./schemas
COPY db ./db
COPY main.py .

CMD ["bash", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
