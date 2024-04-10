FROM postgres:16.0
RUN apt-get update
RUN apt-get install -y postgresql-16-pgvector
