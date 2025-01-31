from celery import Celery
import httpx
import uuid
import os
from pathlib import Path

celery = Celery(
    __name__,
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

GENERATED_IMAGES_DIR = "generated_images"
os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)

@celery.task
def generate_image_task(prompt: str, model: str):
    try:
        filename = f"{uuid.uuid4()}.png"
        file_path = Path(GENERATED_IMAGES_DIR) / filename

        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={"prompt": prompt, "model": model},
            timeout=60
        )
        response.raise_for_status()

        with open(file_path, "wb") as f:
            f.write(response.content)

        return {"url": f"/static/{filename}"}
    except Exception as e:
        raise
