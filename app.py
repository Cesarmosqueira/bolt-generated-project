from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import uuid
import os
import logging
from celery import Celery
from typing import Optional
from pathlib import Path

app = FastAPI()

# Security
api_key_header = APIKeyHeader(name="X-API-KEY")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Celery setup
celery = Celery(
    __name__,
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

# Configuration
GENERATED_IMAGES_DIR = "generated_images"
os.makedirs(GENERATED_IMAGES_DIR, exist_ok=True)

class GenerateRequest(BaseModel):
    prompt: str
    model: Optional[str] = "stable-diffusion"

@app.post("/generate")
async def generate_image(request: GenerateRequest, api_key: str = Depends(api_key_header)):
    task = generate_image_task.delay(request.prompt, request.model)
    return {"task_id": task.id}

@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    task = celery.AsyncResult(task_id)
    return {"status": task.status, "result": task.result}

@app.get("/static/{filename}")
async def get_image(filename: str):
    file_path = Path(GENERATED_IMAGES_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)

@celery.task
def generate_image_task(prompt: str, model: str):
    try:
        # Generate unique filename
        filename = f"{uuid.uuid4()}.png"
        file_path = Path(GENERATED_IMAGES_DIR) / filename

        # Call Ollama API
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={"prompt": prompt, "model": model},
            timeout=60
        )
        response.raise_for_status()

        # Save image
        with open(file_path, "wb") as f:
            f.write(response.content)

        return {"url": f"/static/{filename}"}
    except Exception as e:
        logging.error(f"Error generating image: {str(e)}")
        raise
