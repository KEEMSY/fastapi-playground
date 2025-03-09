FROM python:3.9.6-slim-buster

RUN apt-get update && \
    apt-get install -y gcc libpq-dev && apt-get install -y procps && \
    apt clean && \
    rm -rf /var/cache/apt/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

COPY requirements.txt requirements.txt
RUN pip install -U pip && \
    pip install --no-cache -r requirements.txt

COPY . /home/fastAPI-Playground
# Delete contents of alembic/versions if it exists
RUN if [ -d "/home/fastAPI-Playground/alembic/versions" ]; then \
    rm -rf /home/fastAPI-Playground/alembic/versions/*; \
    fi


# Ensure scripts have executable permissions
RUN chmod +x /home/fastAPI-Playground/scripts/*.sh

ENV PATH "$PATH:/home/fastAPI-Playground/scripts"

RUN useradd -m -d /home/fastAPI-Playground -s /bin/bash app \
    && chown -R app:app /home/fastAPI-Playground

USER app
WORKDIR /home/fastAPI-Playground

CMD ["bash", "./scripts/start-dev.sh"]
# CMD ["bash", "./scripts/start-prod.sh"]