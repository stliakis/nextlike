FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

WORKDIR /app/
COPY . .

RUN apt-get update
RUN apt-get update && apt-get install -y inotify-tools postgresql-client poppler-utils ipython

RUN pip install --no-cache-dir poetry

RUN poetry config virtualenvs.create false
RUN poetry install --no-root

RUN chmod +x app/entrypoint.sh

WORKDIR /app

CMD ["/app/app/entrypoint.sh"]