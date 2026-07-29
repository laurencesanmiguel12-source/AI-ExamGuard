FROM python:3.12-slim

# opencv-contrib-python (the non-headless build this app uses, for cv2.face's LBPH recognizer -
# see app/services/face_service.py) links against these even though nothing here ever calls
# cv2.imshow or opens a window. Without them, `import cv2` fails at container startup.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# This container has no GPU passthrough, so it deliberately stays on the CPU-only wheel index -
# unlike the local dev venv (see requirements.txt's torch/torchvision lines), which was switched
# to a +cu126 build once a real NVIDIA GPU was confirmed available on that machine. A local
# version label (+cpu vs +cu126) is a PEP 440 exact-version distinction, so simply pre-installing
# the CPU build here no longer "already satisfies" requirements.txt's now-+cu126 pin - pip would
# try to upgrade to the CUDA build inside the container instead. Strip those two lines (and the
# CUDA extra-index-url, unneeded here) before the main install so the container reliably stays
# CPU-only regardless of what the local dev pin says.
RUN pip install --no-cache-dir torch==2.13.0 torchvision==0.28.0 \
    --index-url https://download.pytorch.org/whl/cpu
RUN grep -v -E "^(torch(vision)?==|--extra-index-url)" requirements.txt > requirements-docker.txt \
    && pip install --no-cache-dir -r requirements-docker.txt

# ultralytics (above) transitively pulls in opencv-python, which can silently overwrite
# opencv-contrib-python's cv2.face module (confirmed possible in this venv - see the warning
# comment on requirements.txt's opencv-contrib-python line). Currently this specific combination
# still leaves LBPH intact, but that's an install-order coincidence, not a guarantee - fail the
# build loudly here instead of shipping a silently-broken face-verification feature if a future
# dependency bump changes that.
RUN python -c "import cv2; assert hasattr(cv2.face, 'LBPHFaceRecognizer_create'), 'cv2.face.LBPHFaceRecognizer_create missing - opencv-python likely clobbered opencv-contrib-python, see comment above'"

COPY . .

EXPOSE 8000

# Migrations run on every container start rather than as a separate one-off step - alembic is
# idempotent (no-ops if already at head), and this keeps `docker compose up` a single command
# that's always safe to rerun after pulling a new image with new migrations.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
