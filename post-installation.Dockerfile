FROM post-deployment-app-hook:latest

COPY poetry.lock pyproject.toml .
RUN pip --no-cache-dir install poetry && poetry install --no-root --no-cache

COPY .apolo .apolo
RUN poetry install --only-root --no-cache
