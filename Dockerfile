FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends podman && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY src ./src
COPY scripts/podman-remote /usr/local/bin/podman-remote
RUN pip install --no-deps . && useradd -u 1000 -m manim && mkdir /data && chown manim:manim /data
ENV MANIM_HOST=0.0.0.0 MANIM_DATA_DIR=/data MANIM_RUNTIME=podman-remote
USER 1000:1000
EXPOSE 8787
ENTRYPOINT ["chatgpt-manim"]
