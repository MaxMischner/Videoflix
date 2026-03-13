FROM python:3.12-alpine

LABEL maintainer="mihai@developerakademie.com"
LABEL version="1.0"
LABEL description="Python 3.12 Alpine"

WORKDIR /app

COPY backend.entrypoint.sh /usr/local/bin/backend.entrypoint.sh
COPY . .

RUN apk update && \
    apk add --no-cache --upgrade bash && \
    apk add --no-cache postgresql-client ffmpeg && \
    apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
    sed -i 's/\r$//' /usr/local/bin/backend.entrypoint.sh && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps && \
    chmod +x /usr/local/bin/backend.entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/usr/local/bin/backend.entrypoint.sh"]
