FROM docker.io/manimcommunity/manim:v0.22.1
USER root
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir pydantic==2.14.1
COPY src/chatgpt_manim/scene.py /opt/app/chatgpt_manim/scene.py
COPY src/chatgpt_manim/__init__.py /opt/app/chatgpt_manim/__init__.py
COPY worker/render.py /opt/app/render.py
ENV PYTHONPATH=/opt/app HOME=/tmp XDG_CACHE_HOME=/tmp/cache OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
WORKDIR /work
USER 1000:1000
ENTRYPOINT ["python", "/opt/app/render.py"]
