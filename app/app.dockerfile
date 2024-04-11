FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

WORKDIR /app/

RUN apt-get update
RUN apt-get update && apt-get install -y inotify-tools postgresql-client

RUN pip install --no-cache-dir poetry

COPY ./pyproject.toml ./poetry.lock* /app/

RUN poetry config virtualenvs.create false
RUN poetry install --no-root

COPY . /app
RUN chmod +x /app/app/entrypoint.sh

CMD ["/app/app/entrypoint.sh"]