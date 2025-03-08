from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from typing import Optional, List
import insightface
from insightface.app import FaceAnalysis
from insightface.app.common import Face
import cv2
import numpy as np
import tempfile
import uuid
import json
from datetime import datetime
import asyncio

from app.services.ai_services import AIServices
from app.services.video_processor import VideoProcessor

app = FastAPI(title="AI Social Media Content Generator")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
face_analyzer = FaceAnalysis(name='buffalo_l')
face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
ai_services = AIServices()
video_processor = VideoProcessor()

# In-memory storage for job status (replace with database in production)
job_status = {}

class VideoGenerationRequest(BaseModel):
    style: str
    duration: int
    effects: List[str]
    background: Optional[str] = None
    image_path: str

class JobStatus(BaseModel):
    status: str
    progress: int
    result: Optional[dict] = None
    error: Optional[str] = None

async def process_video_generation(job_id: str, image_path: str, request: VideoGenerationRequest):
    try:
        # Update job status
        job_status[job_id]["status"] = "analyzing"
        job_status[job_id]["progress"] = 10

        # Analyze image with OpenAI
        analysis_result = await ai_services.analyze_image(image_path)
        if "error" in analysis_result:
            raise Exception(f"Image analysis failed: {analysis_result['error']}")

        # Update progress
        job_status[job_id]["progress"] = 30
        job_status[job_id]["status"] = "generating_script"

        # Generate video script
        script_result = await ai_services.generate_video_script(
            analysis_result["analysis"],
            request.style,
            request.duration
        )
        if "error" in script_result:
            raise Exception(f"Script generation failed: {script_result['error']}")

        # Update progress
        job_status[job_id]["progress"] = 50
        job_status[job_id]["status"] = "suggesting_effects"

        # Get suggested effects
        effects = await ai_services.suggest_effects(analysis_result["analysis"], request.style)
        if "error" in effects:
            raise Exception(f"Effects suggestion failed: {effects[1]}")

        # Generate video
        job_status[job_id]["progress"] = 70
        job_status[job_id]["status"] = "rendering"

        video_result = video_processor.create_video_from_image(
            image_path=image_path,
            duration=request.duration,
            effects=effects,
            style=request.style,
            background_music=request.background
        )

        if not video_result["success"]:
            raise Exception(f"Video generation failed: {video_result['error']}")

        # Update final status
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["progress"] = 100
        job_status[job_id]["result"] = {
            "script": script_result["script"],
            "effects": effects,
            "analysis": analysis_result["analysis"],
            "video_path": video_result["output_path"],
            "filename": video_result["filename"]
        }

    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["error"] = str(e)

@app.post("/api/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # Process the image with InsightFace
        img = cv2.imread(temp_path)
        faces = face_analyzer.get(img)
        
        if not faces:
            raise HTTPException(status_code=400, detail="No face detected in the image")
        
        # Clean up temporary file
        os.unlink(temp_path)
        
        return {"message": "Photo processed successfully", "face_detected": True}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-video")
async def generate_video(request: VideoGenerationRequest, background_tasks: BackgroundTasks):
    try:
        # Generate a unique job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job status
        job_status[job_id] = {
            "status": "initializing",
            "progress": 0,
            "started_at": datetime.utcnow().isoformat()
        }

        # Start video generation in background
        background_tasks.add_task(
            process_video_generation,
            job_id,
            request.image_path,
            request
        )

        return {
            "message": "Video generation started",
            "job_id": job_id,
            "status": "initializing"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_status[job_id]

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 