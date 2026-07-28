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

# torch/torchvision from the CPU-only wheel index first - the default PyPI wheel pulls in full
# CUDA support (multi-GB download), which this app never uses (inference and training are both
# CPU-only here, see backend/training's own scripts). Installing these first means the plain
# `pip install -r requirements.txt` below sees them already satisfied and won't re-resolve them
# against the CUDA build.
RUN pip install --no-cache-dir torch==2.13.0 torchvision==0.28.0 \
    --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Migrations run on every container start rather than as a separate one-off step - alembic is
# idempotent (no-ops if already at head), and this keeps `docker compose up` a single command
# that's always safe to rerun after pulling a new image with new migrations.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
