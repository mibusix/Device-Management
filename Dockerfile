FROM python:3.11-slim

# 默认与常见 Linux 桌面用户 UID/GID 一致；不一致时可在构建时覆盖
ARG USER_UID=1000
ARG USER_GID=1000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY VERSION .
COPY app/ ./app/

RUN groupadd -g ${USER_GID} appuser && \
    useradd -u ${USER_UID} -g appuser -d /app -s /sbin/nologin appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
