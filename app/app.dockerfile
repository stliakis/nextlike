FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

WORKDIR /app/

RUN apt-get update
RUN apt-get update && apt-get install -y inotify-tools

RUN pip install --no-cache-dir poetry

COPY ./pyproject.toml ./poetry.lock* /app/

RUN poetry config virtualenvs.create false
RUN poetry install --no-root

COPY app /app/nextlike
COPY ./tests /app/tests

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]