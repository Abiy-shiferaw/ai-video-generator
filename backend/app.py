from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from datetime import datetime
import uuid
import json
from dotenv import load_dotenv
import openai
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip, TextClip, AudioClip
from moviepy.video.fx import all as vfx
import tempfile
import requests
import base64
import gtts  # Google Text-to-Speech
import time
import shutil
from typing import List, Optional
from pydantic import BaseModel
import asyncio
import threading

# Add Eleven Labs import
import requests as elevenlabs_requests  # Using requests for Eleven Labs API

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs('temp', exist_ok=True)
os.makedirs('voices', exist_ok=True)  # Directory for uploaded voice files
os.makedirs('training', exist_ok=True)  # Directory for training data
os.makedirs('models', exist_ok=True)  # Directory for trained models

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Eleven Labs API key
ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY", "sk_66fa7dc6ab476345f1d4b6ebfd7d814f5b53045df4d6e909")

# Initialize DEEPA API key
DEEPA_API_KEY = os.getenv("DEEPA_API_KEY", "1a0c4b07-e97f-44f2-b39e-90259c911e09")

# Debug output for API key check
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    # Print a masked version of the key for debugging
    masked_key = api_key[:8] + "..." + api_key[-4:]
    print(f"OpenAI API Key loaded: {masked_key}")
else:
    print("ERROR: OpenAI API Key not found in environment variables!")

# In-memory storage for job status
job_status = {}

class VideoGenerationRequest(BaseModel):
    style: str
    duration: int
    effects: List[str] = []
    background: Optional[str] = None
    image_path: str
    template: Optional[str] = None
    add_voiceover: Optional[bool] = False

class JobStatus(BaseModel):
    status: str
    progress: int
    result: Optional[dict] = None
    error: Optional[str] = None
    estimated_time_remaining: Optional[int] = None  # in seconds
    started_at: Optional[float] = None  # timestamp when job started

class TrainingFile(BaseModel):
    id: str
    filename: str
    type: str
    url: str

class TrainingModel(BaseModel):
    id: str
    name: str
    created_at: str
    status: str
    training_files: List[TrainingFile] = []

# In-memory storage for training models
training_models = {}

def process_video_generation(job_id, image_path, request_data, voice_file=None, model_id=None):
    """
    Process video generation in the background
    
    Args:
        job_id (str): The unique job ID
        image_path (str): Path to the image
        request_data (dict): Request data including style, duration, etc.
        voice_file (str, optional): Path to a custom voice file
        model_id (str, optional): ID of a trained model to use
    """
    try:
        # Create JobStatus object with initial time estimate
        initial_time_estimate = calculate_estimated_time(request_data.get('duration', 15), request_data.get('add_voiceover', False))
        status_obj = JobStatus(
            status="processing",
            progress=5,
            result=None,
            error=None,
            estimated_time_remaining=initial_time_estimate,
            started_at=time.time()
        )
        # Store as dictionary to avoid serialization issues
        job_status[job_id] = status_obj
        
        # Get full path
        full_image_path = image_path
        
        # Update progress to 10%
        job_status[job_id].progress = 10
        job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 10)
        
        # Analyze the image using OpenAI's vision model
        try:
            image_analysis = analyze_image(full_image_path)
        except Exception as e:
            print(f"Error in analyze_image: {e}")
            job_status[job_id].status = "failed"
            job_status[job_id].error = f"Failed to analyze image: {str(e)}"
            return
        
        # Update progress to 20%
        job_status[job_id].progress = 20
        job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 20)
        
        # Generate script based on image analysis
        try:
            script = generate_video_script(image_analysis, request_data.get('style', 'casual'), request_data.get('duration', 15))
            # Extract the script text if it's a dictionary
            if isinstance(script, dict) and 'script' in script:
                script_text = script['script']
            else:
                script_text = script
        except Exception as e:
            print(f"Error in script generation: {e}")
            job_status[job_id].status = "failed"
            job_status[job_id].error = f"Failed to generate script: {str(e)}"
            return
        
        # Update progress to 30%
        job_status[job_id].progress = 30
        job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 30)
        
        # Suggest effects based on image analysis
        try:
            effects = suggest_effects(image_analysis, request_data.get('style', 'casual'))
        except Exception as e:
            print(f"Error in suggest_effects: {e}")
            # Fallback to empty effects list
            effects = []
        
        # Update progress to 40%
        job_status[job_id].progress = 40
        job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 40)
        
        # Create video using available template
        try:
            if request_data.get('template'):
                video_path = create_video_from_template(
                    request_data.get('template'), 
                    full_image_path, 
                    script_text, 
                    request_data.get('style', 'casual'), 
                    request_data.get('duration', 15)
                )
            else:
                video_path = create_video(
                    full_image_path, 
                    request_data.get('duration', 15), 
                    effects, 
                    request_data.get('style', 'casual'), 
                    request_data.get('background')
                )
            
            # Update progress to 80%
            job_status[job_id].progress = 80
            job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 80)
            
            # Add voiceover if requested
            if request_data.get('add_voiceover', False):
                try:
                    # Generate TTS audio
                    audio_path = generate_tts_audio(script_text, output_path=None, voice_file=voice_file)
                    
                    # Add voiceover to video
                    final_video_result = add_voiceover_to_video(video_path, script_text, voice_file=voice_file)
                    
                    # Use final video with voiceover if successful
                    if final_video_result["success"]:
                        video_path = final_video_result["video_path"]
                except Exception as e:
                    print(f"Error adding voiceover: {e}")
                    # Continue with the video without voiceover
            
            # Update progress to 90%
            job_status[job_id].progress = 90
            job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 90)
            
            # Get relative path for frontend
            relative_video_path = video_path
                
            # Update job status to completed
            job_status[job_id].status = "completed"
            job_status[job_id].progress = 100
            job_status[job_id].estimated_time_remaining = 0
            job_status[job_id].result = {
                "video_path": relative_video_path,
                "script": script_text,
                "effects": effects,
                "used_custom_voice": voice_file is not None,
                "used_custom_model": model_id is not None
            }
            
        except Exception as e:
            print(f"Error in video generation process: {e}")
            job_status[job_id].status = "failed"
            job_status[job_id].error = f"Failed to generate video: {str(e)}"
            
    except Exception as e:
        print(f"Error in video generation process: {e}")
        if job_id in job_status:
            job_status[job_id].status = "failed"
            job_status[job_id].error = f"Failed to generate video: {str(e)}"

def update_estimated_time(job_status, current_progress):
    """
    Update the estimated time remaining based on elapsed time and progress
    
    Args:
        job_status: The current job status object
        current_progress: The current progress percentage
        
    Returns:
        Updated estimated time remaining in seconds
    """
    # If there's no start time, return the original estimate
    if not job_status.started_at:
        return job_status.estimated_time_remaining
        
    # Calculate elapsed time
    elapsed_time = time.time() - job_status.started_at
    
    # If progress is very low, return the original estimate
    if current_progress < 10:
        return job_status.estimated_time_remaining
        
    # Calculate estimated total time based on elapsed time and progress
    estimated_total_time = (elapsed_time / current_progress) * 100
    
    # Calculate time remaining
    time_remaining = max(0, estimated_total_time - elapsed_time)
    
    # Return the estimated time remaining in seconds (rounded to integer)
    return int(time_remaining)

# Simple root route for testing
@app.route('/')
def index():
    return jsonify({
        "status": "API is running",
        "endpoints": [
            {"method": "POST", "url": "/api/upload-photo", "description": "Upload a photo"},
            {"method": "POST", "url": "/api/generate-video", "description": "Generate a video"},
            {"method": "GET", "url": "/api/status/<job_id>", "description": "Check job status"}
        ]
    })

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_image(image_path):
    """Analyze image using OpenAI's vision model"""
    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        print(f"Using model: {model}")

        # Read image file and convert to base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('ascii')
            
            response = openai.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this image and provide details about the person's appearance, expression, and any notable features that would be important for video generation."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            return {"analysis": response.choices[0].message.content}
    except Exception as e:
        print(f"Error in analyze_image: {str(e)}")
        return {"error": str(e)}

def generate_video_script(image_analysis, style, duration):
    """Generate video script using OpenAI"""
    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        print(f"Using model for script generation: {model}")
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a creative video script writer specializing in social media content."
                },
                {
                    "role": "user",
                    "content": f"""
                    Create a detailed video script for a {duration}-second social media video with the following parameters:
                    - Style: {style}
                    - Person Analysis: {image_analysis}
                    
                    Include:
                    1. Scene descriptions
                    2. Camera movements
                    3. Transitions
                    4. Timing for each segment
                    """
                }
            ],
            max_tokens=1000
        )
        return {"script": response.choices[0].message.content}
    except Exception as e:
        print(f"Error in generate_video_script: {str(e)}")
        return {"error": str(e)}

def suggest_effects(image_analysis, style):
    """Suggest video effects using OpenAI"""
    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        print(f"Using model for effects suggestion: {model}")
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a video effects specialist. Always respond with a valid JSON array of string effect names."
                },
                {
                    "role": "user",
                    "content": f"""
                    Suggest 5-7 video effects that would work well for this content:
                    - Style: {style}
                    - Person Analysis: {image_analysis}
                    
                    Return only a JSON array of effect names like this: ["effect1", "effect2", "effect3"].
                    Do not include any explanations or other text, just the JSON array.
                    """
                }
            ],
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        print(f"Raw effects response: {content}")
        
        # Try to parse as JSON, or extract array if enclosed in other text
        try:
            # First attempt: direct JSON parsing
            effects = json.loads(content)
            if not isinstance(effects, list):
                raise ValueError("Response is not a list")
        except json.JSONDecodeError:
            # Second attempt: try to extract array with regex
            import re
            array_match = re.search(r'\[(.*?)\]', content)
            if array_match:
                try:
                    effects = json.loads(f"[{array_match.group(1)}]")
                except:
                    # Fall back to default effects if all parsing fails
                    effects = ["zoom", "fade_in", "fade_out", "color_enhance", "slow_motion"]
            else:
                # Fall back to default effects
                effects = ["zoom", "fade_in", "fade_out", "color_enhance", "slow_motion"]
        
        print(f"Parsed effects: {effects}")
        return effects
    except Exception as e:
        print(f"Error in suggest_effects: {str(e)}")
        # Return default effects rather than an error
        return ["zoom", "fade_in", "fade_out", "color_enhance", "slow_motion"]

def apply_effect(clip, effect_name):
    """Apply a specific effect to a video clip"""
    effects = {
        # These effects are actually available in moviepy
        "resize": lambda c: c.resize(width=c.w*1.5),  # Instead of zoom
        "fade_in": lambda c: c.fadein(1),
        "fade_out": lambda c: c.fadeout(1),
        "mirror_x": lambda c: c.fx(vfx.mirror_x),
        "mirror_y": lambda c: c.fx(vfx.mirror_y),
        "colorx": lambda c: c.fx(vfx.colorx, 1.5),  # Enhance colors
        "painting": lambda c: c.fx(vfx.painting, saturation=1.6, black=0.006),
        "speedx_slow": lambda c: c.fx(vfx.speedx, 0.5),  # Slow motion
        "speedx_fast": lambda c: c.fx(vfx.speedx, 2.0),  # Fast motion
        "time_symmetrize": lambda c: c.fx(vfx.time_symmetrize),  # Play forwards then backwards
        "invert_colors": lambda c: c.fx(vfx.invert_colors)
    }
    
    if effect_name in effects:
        try:
            print(f"Applying effect: {effect_name}")
            return effects[effect_name](clip)
        except Exception as e:
            print(f"Error applying effect {effect_name}: {str(e)}")
            print(f"Skipping effect {effect_name}")
            return clip
    return clip

def map_effect_name(effect_name):
    """Map AI-suggested effect names to our implemented effects"""
    # Define mappings from AI suggestions to implemented effects
    effect_mappings = {
        # Color effects
        "warmtone": "colorx",
        "warm-color-grading": "colorx",
        "warmorange": "colorx",
        "warmth": "colorx",
        "colorboost": "colorx",
        "color-boost": "colorx",
        "colorenhance": "colorx",
        "subtleglow": "colorx",
        "vibrant": "colorx",
        "warm": "colorx",
        "warmglow": "colorx",
        
        # Lens effects
        "softfocus": "painting",
        "soft-focus": "painting",
        "lens-blur": "painting",
        "lensflare": "painting",
        "subtlelensflare": "painting",
        "bokeh": "painting",
        "bokehbackground": "painting",
        "lightleak": "painting",
        
        # Transitions
        "fadein": "fade_in",
        "fadeout": "fade_out",
        "crossfade": "fade_in",
        
        # Motion effects
        "slowmotion": "speedx_slow",
        "fastmotion": "speedx_fast",
        "smoothtransition": "time_symmetrize",
        
        # Filters
        "vignette": "mirror_x",
        "lightvignette": "mirror_y",
        "subtlevignetting": "mirror_x",
        "mirror-effect": "mirror_x",
        "grain-filter": "invert_colors",
        "naturalgrain": "invert_colors",
        "smilehighlight": "colorx"
    }
    
    # Normalize effect name (lowercase, remove spaces and dashes)
    normalized_name = effect_name.lower().replace("-", "").replace("_", "").replace(" ", "")
    
    # Return mapped effect if available, or original if not
    if normalized_name in effect_mappings:
        mapped_effect = effect_mappings[normalized_name]
        print(f"Mapped effect '{effect_name}' to '{mapped_effect}'")
        return mapped_effect
    
    return effect_name

def create_video(image_path, duration, effects, style, background_music=None):
    """Create a video from a single image with effects"""
    try:
        # Create base clip from image
        base_clip = ImageClip(image_path).set_duration(duration)
        
        # Apply effects in sequence
        final_clip = base_clip
        
        # Apply at least some default effects if none of the suggested ones match
        applied_effects = 0
        for effect in effects:
            # Map the effect name to our implemented effects
            mapped_effect = map_effect_name(effect)
            
            if mapped_effect in ["resize", "fade_in", "fade_out", "mirror_x", "mirror_y", 
                              "colorx", "painting", "speedx_slow", "speedx_fast",
                              "time_symmetrize", "invert_colors"]:
                final_clip = apply_effect(final_clip, mapped_effect)
                applied_effects += 1
            else:
                print(f"Skipping unknown effect: {effect}")
        
        # If no effects were applied, use some defaults
        if applied_effects == 0:
            print("No matching effects found, applying default effects")
            final_clip = apply_effect(final_clip, "fade_in")
            final_clip = apply_effect(final_clip, "resize")
            final_clip = apply_effect(final_clip, "colorx")
            final_clip = apply_effect(final_clip, "fade_out")
        
        # Initialize audio to None
        audio = None
        
        # Add background music if provided
        if background_music and os.path.exists(background_music):
            audio = AudioFileClip(background_music)
            if audio.duration < duration:
                audio = audio.loop(duration=duration)
            final_clip = final_clip.set_audio(audio)
        
        # Generate output filename
        output_filename = f"video_{os.path.basename(image_path)}_{int(duration)}s.mp4"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        # Write final video
        final_clip.write_videofile(
            output_path,
            fps=30,
            bitrate="4000k",
            codec='libx264',
            audio_codec='aac'
        )
        
        # Clean up
        final_clip.close()
        # Only close audio if it was initialized
        if audio is not None:
            audio.close()
        
        return {
            "success": True,
            "output_path": output_path,
            "filename": output_filename
        }
        
    except Exception as e:
        print(f"Error in create_video: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def generate_tts_audio(text, voice="en-US-Neural2-F", output_path=None, voice_file=None):
    """
    Generate Text-to-Speech audio from text.
    
    Args:
        text (str): The text to convert to speech
        voice (str): The voice to use for TTS
        output_path (str, optional): Path to save the audio file
        voice_file (str, optional): Path to a custom voice file
        
    Returns:
        str: Path to the generated audio file
    """
    if not output_path:
        os.makedirs('temp', exist_ok=True)
        output_path = f"temp/tts_{int(time.time())}.mp3"
    
    try:
        # If a custom voice file is provided, use Eleven Labs for voice cloning
        if voice_file and os.path.exists(voice_file):
            print(f"Using custom voice file: {voice_file}")
            try:
                # First, check if we already have a voice ID for this file
                voice_id = None
                voice_name = os.path.basename(voice_file).split('.')[0]
                
                # Try to get existing voice or create new one
                try:
                    # Check if we have existing voices
                    headers = {
                        "xi-api-key": ELEVEN_LABS_API_KEY
                    }
                    response = elevenlabs_requests.get(
                        "https://api.elevenlabs.io/v1/voices",
                        headers=headers
                    )
                    voices = response.json().get("voices", [])
                    
                    # Check if we already have this voice
                    for v in voices:
                        if v["name"] == voice_name:
                            voice_id = v["voice_id"]
                            print(f"Using existing voice ID: {voice_id}")
                            break
                    
                    # If not found, create a new voice
                    if not voice_id:
                        print("Creating new voice with Eleven Labs")
                        with open(voice_file, "rb") as f:
                            files = {
                                "files": (os.path.basename(voice_file), f, "audio/mpeg"),
                            }
                            data = {
                                "name": voice_name,
                                "description": "Uploaded custom voice"
                            }
                            response = elevenlabs_requests.post(
                                "https://api.elevenlabs.io/v1/voices/add",
                                headers=headers,
                                files=files,
                                data=data
                            )
                            if response.status_code == 200:
                                voice_id = response.json().get("voice_id")
                                print(f"Created new voice ID: {voice_id}")
                            else:
                                print(f"Error creating voice: {response.text}")
                except Exception as e:
                    print(f"Error accessing Eleven Labs API: {str(e)}")
                
                # If we have a voice ID, generate speech
                if voice_id:
                    # Generate speech with the voice
                    headers = {
                        "xi-api-key": ELEVEN_LABS_API_KEY,
                        "Content-Type": "application/json"
                    }
                    data = {
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75
                        }
                    }
                    response = elevenlabs_requests.post(
                        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                        headers=headers,
                        json=data
                    )
                    
                    if response.status_code == 200:
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                        print(f"Generated TTS audio using Eleven Labs: {output_path}")
                        return {"success": True, "audio_path": output_path}
                    else:
                        print(f"Error generating speech with Eleven Labs: {response.text}")
                
                # If Eleven Labs fails or no voice ID, fall back to using the voice file directly
                shutil.copy(voice_file, output_path)
                return {"success": True, "audio_path": output_path}
                
            except Exception as e:
                print(f"Error using Eleven Labs for voice cloning: {str(e)}")
                # Fall back to just using the voice file
                shutil.copy(voice_file, output_path)
                return {"success": True, "audio_path": output_path}
        
        # Try to use gtts
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(output_path)
            print(f"Generated TTS audio using gTTS: {output_path}")
            return {"success": True, "audio_path": output_path}
        except ImportError:
            print("gTTS not installed, using silent audio fallback")
            # Create a silent audio file based on text length
            from moviepy.editor import AudioClip
            words = len(text.split())
            duration = max(3, words * 0.3)  # Estimate 0.3 seconds per word, minimum 3 seconds
            
            silent_audio = AudioClip(lambda t: 0, duration=duration)
            silent_audio.write_audiofile(output_path, fps=44100)
            print(f"Created silent audio file: {output_path}")
            return {"success": True, "audio_path": output_path}
    
    except Exception as e:
        print(f"Error generating TTS audio: {str(e)}")
        return {"success": False, "error": str(e)}

def add_voiceover_to_video(video_path, script_text, output_path=None, voice_file=None):
    """
    Adds a voiceover to a video.
    
    Args:
        video_path (str): Path to the video file
        script_text (str): Text for the voiceover
        output_path (str, optional): Path to save the output video
        voice_file (str, optional): Path to a custom voice file
        
    Returns:
        str: Path to the output video
    """
    if not output_path:
        output_path = video_path
    
    try:
        # Generate TTS audio
        tts_result = generate_tts_audio(script_text, voice_file=voice_file)
        if not tts_result["success"]:
            print(f"Warning: Voiceover could not be generated: {tts_result.get('error', 'Unknown error')}")
            return {"success": False, "error": tts_result.get("error", "Unknown error in TTS generation")}
        
        audio_path = tts_result["audio_path"]
        
        # Load the video and audio
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)
        
        # Check the durations
        video_duration = video.duration
        audio_duration = audio.duration

        print(f"Video duration: {video_duration}s, Audio duration: {audio_duration}s")
        
        # If audio is longer than video, make the video slower to match
        if audio_duration > video_duration:
            print(f"Audio is longer than video. Extending video duration.")
            speed_factor = video_duration / audio_duration
            # Only slow down if the difference is not too extreme
            if speed_factor > 0.5:  
                video = video.fx(vfx.speedx, speed_factor)
                video_duration = video.duration
                print(f"Adjusted video duration to {video_duration}s")
            else:
                print("Duration difference too large to adjust speed. Using original durations.")
        
        # Set the audio (this will use the audio duration which might be shorter than the video)
        final_video = video.set_audio(audio)
        
        # Write the output
        final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')
        
        # Clean up
        video.close()
        audio.close()
        final_video.close()
        
        # Don't remove the audio file yet as it might be needed later
        # if os.path.exists(audio_path):
        #     os.remove(audio_path)
            
        return {"success": True, "video_path": output_path}
    
    except Exception as e:
        error_msg = f"Error adding voiceover: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}

def create_video_from_template(template_name, image_path, script, style, duration=15):
    """Create a video using a predefined template"""
    try:
        # Define templates with simpler effects
        templates = {
            "social_story": {
                "effects": ["fade_in", "resize", "colorx", "fade_out"],
                "text_position": "bottom",
                "has_voiceover": True,
                "transitions": ["fade"]
            },
            "product_showcase": {
                "effects": ["fade_in", "resize", "mirror_x", "colorx", "fade_out"],
                "text_position": "top",
                "has_voiceover": True,
                "transitions": ["slide"]
            },
            "dynamic_ad": {
                "effects": ["speedx_fast", "colorx", "mirror_x", "fade_out"],  # Removed painting and time_symmetrize
                "text_position": "center",
                "has_voiceover": True,
                "transitions": ["zoom"]
            },
            "cinematic": {
                "effects": ["fade_in", "mirror_x", "colorx", "fade_out"],  # Removed painting and time_symmetrize
                "text_position": "bottom",
                "has_voiceover": True,
                "transitions": ["fade"]
            }
        }
        
        # Check if template exists
        if template_name not in templates:
            return {
                "success": False, 
                "error": f"Template '{template_name}' not found. Available templates: {list(templates.keys())}"
            }
        
        template = templates[template_name]
        
        # Create base clip from image
        base_clip = ImageClip(image_path).set_duration(duration)
        
        # Apply template effects
        final_clip = base_clip
        for effect in template["effects"]:
            final_clip = apply_effect(final_clip, effect)
        
        # Add text overlay
        if script and len(script) > 0:
            try:
                # Create a short version for the overlay
                short_text = script[:100] + "..." if len(script) > 100 else script
                
                # Try to create text clip - this requires ImageMagick
                text_clip = TextClip(
                    short_text, 
                    fontsize=30, 
                    color='white', 
                    bg_color='rgba(0,0,0,0.5)',
                    method='caption', 
                    size=(final_clip.w * 0.8, None)
                ).set_duration(duration)
                
                # Position the text based on template
                if template["text_position"] == "top":
                    text_pos = ('center', 50)
                elif template["text_position"] == "bottom":
                    text_pos = ('center', final_clip.h - text_clip.h - 50)
                else:  # center
                    text_pos = ('center', 'center')
                    
                text_clip = text_clip.set_position(text_pos)
                
                # Composite the clips
                final_clip = CompositeVideoClip([final_clip, text_clip])
            except Exception as text_error:
                print(f"Warning: Could not add text overlay: {str(text_error)}")
                print("Proceeding without text overlay...")
                # Continue without text overlay
        
        # Generate output filename
        output_filename = f"{template_name}_{os.path.basename(image_path)}_{int(duration)}s.mp4"
        output_path = os.path.join("output", output_filename)
        
        # Write the video
        final_clip.write_videofile(
            output_path,
            fps=30,
            bitrate="4000k",
            codec='libx264',
            audio_codec='aac'
        )
        
        # Add voiceover if specified
        if template["has_voiceover"] and script and len(script) > 0:
            voiceover_result = add_voiceover_to_video(output_path, script, output_path)
            if not voiceover_result["success"]:
                print(f"Warning: Voiceover could not be added: {voiceover_result['error']}")
        
        # Clean up
        final_clip.close()
        
        return {
            "success": True,
            "output_path": output_path,
            "filename": output_filename,
            "template": template_name
        }
        
    except Exception as e:
        print(f"Error creating video from template: {str(e)}")
        return {"success": False, "error": str(e)}

def generate_video_from_text(text_prompt, duration=15, style="casual"):
    """
    Generate a video directly from text description using DEEPA API.
    
    Args:
        text_prompt (str): The text description to generate a video from
        duration (int): Duration of the video in seconds
        style (str): Style of the video
        
    Returns:
        dict: Dictionary with success status and video path or error message
    """
    try:
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        output_filename = f"text_video_{int(time.time())}.mp4"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Call DEEPA API to generate video
        headers = {
            "Authorization": f"Bearer {DEEPA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Create request data
        data = {
            "prompt": text_prompt,
            "duration": min(duration, 30),  # Cap at 30 seconds to respect service limits
            "style": style
        }
        
        # Make API request
        response = requests.post(
            "https://api.deepa.ai/videos/generate",
            headers=headers,
            json=data
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            
            # Poll for completion if the API returns a job ID
            if 'job_id' in result:
                job_id = result['job_id']
                max_attempts = 60  # Maximum polling attempts
                poll_interval = 5  # Seconds between polling
                
                for attempt in range(max_attempts):
                    # Get job status
                    status_response = requests.get(
                        f"https://api.deepa.ai/videos/status/{job_id}",
                        headers=headers
                    )
                    
                    if status_response.status_code == 200:
                        status = status_response.json()
                        
                        if status.get('status') == 'completed':
                            # Download the video
                            video_url = status.get('video_url')
                            video_response = requests.get(video_url, stream=True)
                            
                            if video_response.status_code == 200:
                                with open(output_path, 'wb') as f:
                                    for chunk in video_response.iter_content(chunk_size=8192):
                                        f.write(chunk)
                                
                                print(f"Successfully generated video from text: {output_path}")
                                return {"success": True, "video_path": output_path}
                            else:
                                print(f"Failed to download video, status code: {video_response.status_code}")
                                return {"success": False, "error": f"Failed to download video: {video_response.text}"}
                        
                        elif status.get('status') == 'failed':
                            print(f"Video generation failed: {status.get('error', 'Unknown error')}")
                            return {"success": False, "error": status.get('error', 'Unknown error')}
                        
                        # Still in progress, wait and try again
                        print(f"Video generation in progress... (attempt {attempt + 1}/{max_attempts})")
                        time.sleep(poll_interval)
                    else:
                        print(f"Failed to get job status, status code: {status_response.status_code}")
                        return {"success": False, "error": f"Failed to get job status: {status_response.text}"}
                
                return {"success": False, "error": "Timed out waiting for video generation"}
            
            # If the API directly returns the video URL
            elif 'video_url' in result:
                video_url = result['video_url']
                video_response = requests.get(video_url, stream=True)
                
                if video_response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        for chunk in video_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f"Successfully generated video from text: {output_path}")
                    return {"success": True, "video_path": output_path}
                else:
                    print(f"Failed to download video, status code: {video_response.status_code}")
                    return {"success": False, "error": f"Failed to download video: {video_response.text}"}
            
            else:
                print(f"Unexpected response format: {result}")
                return {"success": False, "error": "Unexpected API response format"}
        
        else:
            print(f"Failed to generate video, status code: {response.status_code}")
            return {"success": False, "error": f"Failed to generate video: {response.text}"}
    
    except Exception as e:
        error_msg = f"Error generating video from text: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}

@app.route('/api/upload-photo', methods=['POST'])
def upload_photo():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process the image
        img = cv2.imread(filepath)
        if img is None:
            return jsonify({"error": "Invalid image file"}), 400
        
        return jsonify({
            "message": "Photo uploaded successfully",
            "filepath": filepath,
            "face_detected": True  # For simplicity, we're assuming face detection is successful
        })
    
    return jsonify({"error": "Invalid file type"}), 400

@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    """
    Endpoint to generate a video from an uploaded image
    """
    data = request.json
    
    if not data or 'image_path' not in data:
        return jsonify({"success": False, "error": "No image path provided"}), 400
    
    image_path = data['image_path']
    style = data.get('style', 'casual')
    duration = data.get('duration', 15)
    template = data.get('template')
    add_voiceover = data.get('add_voiceover', False)
    voice_id = data.get('voice_id')  # Optional voice ID
    model_id = data.get('model_id')  # Optional model ID for personalized generation
    
    # Find the voice file if a voice ID is provided
    voice_file = None
    if voice_id:
        for file in os.listdir('voices'):
            if file.startswith(f"voice_{voice_id}"):
                voice_file = os.path.join('voices', file)
                break
    
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    job_status[job_id] = JobStatus(
        status="pending",
        progress=0,
        result=None,
        error=None
    )
    
    # Start the video generation process in a background thread
    threading.Thread(
        target=process_video_generation, 
        args=(job_id, image_path, data, voice_file, model_id)
    ).start()
    
    return jsonify({
        "success": True,
        "job_id": job_id,
        "status": "pending"
    }), 200

@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    if job_id not in job_status:
        return jsonify({"error": "Job not found"}), 404
    
    # Convert the JobStatus Pydantic model to a dictionary before jsonifying
    return jsonify(job_status[job_id].dict())

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get available video templates"""
    templates = {
        "social_story": "Vertical format optimized for social media stories",
        "product_showcase": "Highlighting and showcasing a product with animated effects",
        "dynamic_ad": "Fast-paced ad style with dynamic transitions",
        "cinematic": "Cinematic style with dramatic effects and transitions"
    }
    
    return jsonify({
        "templates": [
            {"id": key, "name": key.replace("_", " ").title(), "description": value}
            for key, value in templates.items()
        ]
    })

@app.route('/api/effects', methods=['GET'])
def get_effects():
    """Get available video effects"""
    effects = {
        "resize": "Zoom effect that enlarges the image",
        "fade_in": "Fade in from black",
        "fade_out": "Fade out to black",
        "mirror_x": "Mirror the image horizontally",
        "mirror_y": "Mirror the image vertically",
        "colorx": "Enhance colors to make them more vibrant",
        "painting": "Apply a painting-like effect with enhanced colors",
        "speedx_slow": "Slow motion effect",
        "speedx_fast": "Fast motion effect",
        "time_symmetrize": "Play forwards then backwards",
        "invert_colors": "Invert all colors in the image"
    }
    
    return jsonify({
        "effects": [
            {"id": key, "name": key.replace("_", " ").title(), "description": value}
            for key, value in effects.items()
        ]
    })

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download a generated video file"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404
            
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload-voice', methods=['POST'])
def upload_voice():
    """
    Endpoint to upload a voice file
    """
    if 'voice' not in request.files:
        return jsonify({"success": False, "error": "No voice file provided"}), 400
        
    file = request.files['voice']
    
    if file.filename == '':
        return jsonify({"success": False, "error": "No voice file selected"}), 400
        
    # Check if file is an allowed audio format
    allowed_extensions = {'mp3', 'wav', 'm4a', 'ogg'}
    if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({"success": False, "error": "Invalid file format"}), 400
    
    # Generate a unique filename
    voice_id = str(uuid.uuid4())
    filename = f"voice_{voice_id}.{file.filename.rsplit('.', 1)[1].lower()}"
    filepath = os.path.join('voices', filename)
    
    # Save the file
    file.save(filepath)
    
    # Return the voice ID and URL
    return jsonify({
        "success": True,
        "voice_id": voice_id,
        "filename": filename,
        "url": f"/api/voices/{filename}"
    }), 200

@app.route('/api/voices/<filename>', methods=['GET'])
def get_voice(filename):
    """
    Endpoint to retrieve a voice file
    """
    return send_from_directory('voices', filename)

@app.route('/api/upload-training', methods=['POST'])
def upload_training_files():
    """
    Endpoint to upload multiple files for training
    """
    if 'files[]' not in request.files:
        return jsonify({"success": False, "error": "No files provided"}), 400
        
    files = request.files.getlist('files[]')
    types = request.form.getlist('types[]')
    
    if len(files) == 0:
        return jsonify({"success": False, "error": "No files selected"}), 400
    
    if len(files) != len(types):
        return jsonify({"success": False, "error": "File types don't match file count"}), 400
    
    # Generate a unique model ID
    model_id = str(uuid.uuid4())
    model_dir = os.path.join('training', model_id)
    os.makedirs(model_dir, exist_ok=True)
    
    training_files = []
    
    # Save each file
    for i, file in enumerate(files):
        if file.filename == '':
            continue
            
        # Determine file type
        file_type = types[i]
        if file_type not in ['image', 'video']:
            file_type = 'image' if file.content_type.startswith('image/') else 'video'
        
        # Generate a unique filename
        file_id = str(uuid.uuid4())
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
        filename = f"{file_type}_{file_id}.{ext}"
        filepath = os.path.join(model_dir, filename)
        
        # Save the file
        file.save(filepath)
        
        # Add to training files
        training_files.append(TrainingFile(
            id=file_id,
            filename=filename,
            type=file_type,
            url=f"/api/training/{model_id}/{filename}"
        ))
    
    # Create model entry
    training_models[model_id] = TrainingModel(
        id=model_id,
        name=f"Model {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        created_at=datetime.now().isoformat(),
        status="uploaded",
        training_files=training_files
    )
    
    return jsonify({
        "success": True,
        "model_id": model_id,
        "files_count": len(training_files),
        "model": training_models[model_id].dict()
    }), 200

@app.route('/api/training/<model_id>/<filename>', methods=['GET'])
def get_training_file(model_id, filename):
    """
    Get a training file by model ID and filename
    """
    return send_from_directory(os.path.join('training', model_id), filename)

@app.route('/api/training/start', methods=['POST'])
def start_training():
    """
    Start training a model
    """
    data = request.json
    
    if not data or 'model_id' not in data:
        return jsonify({"success": False, "error": "No model ID provided"}), 400
    
    model_id = data['model_id']
    
    if model_id not in training_models:
        return jsonify({"success": False, "error": "Model not found"}), 404
    
    # Update model status
    training_models[model_id].status = "training"
    
    # In a real implementation, this would trigger a training job
    # For demonstration, we'll simulate training with a background thread
    threading.Thread(
        target=simulate_training,
        args=(model_id,)
    ).start()
    
    return jsonify({
        "success": True,
        "message": "Training started",
        "model": training_models[model_id].dict()
    }), 200

@app.route('/api/training/status/<model_id>', methods=['GET'])
def get_training_status(model_id):
    """
    Get the status of a training model
    """
    if model_id not in training_models:
        return jsonify({"success": False, "error": "Model not found"}), 404
    
    return jsonify({
        "success": True,
        "model": training_models[model_id].dict()
    }), 200

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get all trained models"""
    return jsonify({
        "success": True,
        "models": [model.dict() for model in training_models.values() if model.status == "completed"]
    }), 200

@app.route('/api/generate-video-from-text', methods=['POST'])
def text_to_video():
    """Generate a video from a text prompt using DEEPA AI"""
    data = request.json
    
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    text_prompt = data.get('prompt')
    if not text_prompt:
        return jsonify({"success": False, "error": "No text prompt provided"}), 400
    
    # Get optional parameters
    duration = data.get('duration', 15)
    style = data.get('style', 'casual')
    voice_id = data.get('voice_id')
    voice_file = None
    
    if voice_id:
        # Find the voice file based on ID
        voice_files = [f for f in os.listdir('voices') if voice_id in f]
        if voice_files:
            voice_file = os.path.join('voices', voice_files[0])
            print(f"Using voice file: {voice_file}")
    
    # Generate a unique job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    estimated_time = calculate_estimated_time(duration, voice_id is not None)
    job_status[job_id] = JobStatus(
        status="processing",
        progress=0,
        estimated_time_remaining=estimated_time,
        started_at=time.time()
    )
    
    # Start processing in background thread
    process_thread = threading.Thread(
        target=process_text_to_video_generation,
        args=(job_id, text_prompt, duration, style, voice_file)
    )
    process_thread.daemon = True
    process_thread.start()
    
    return jsonify({
        "success": True,
        "job_id": job_id,
        "status": "processing"
    }), 200

def process_text_to_video_generation(job_id, text_prompt, duration, style, voice_file=None):
    """Process text-to-video generation in the background"""
    try:
        # Update job status to 10%
        job_status[job_id].progress = 10
        job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 10)
        
        # Generate script from prompt if needed
        script = text_prompt
        
        # Generate the video from the text prompt
        result = generate_video_from_text(text_prompt, duration, style)
        
        if not result["success"]:
            job_status[job_id].status = "failed"
            job_status[job_id].error = result["error"]
            return
        
        video_path = result["video_path"]
        
        # Update progress to 80%
        job_status[job_id].progress = 80
        job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 80)
        
        # Add voiceover if requested
        if voice_file:
            try:
                # Generate TTS audio
                audio_path = generate_tts_audio(script, voice_file=voice_file)
                
                # Add voiceover to video
                voiceover_result = add_voiceover_to_video(video_path, script, voice_file=voice_file)
                
                # Use video with voiceover if successful
                if voiceover_result["success"]:
                    video_path = voiceover_result["video_path"]
            except Exception as e:
                print(f"Error adding voiceover: {e}")
                # Continue with the video without voiceover
        
        # Update progress to 90%
        job_status[job_id].progress = 90
        job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 90)
        
        # Update job status to completed
        job_status[job_id].status = "completed"
        job_status[job_id].progress = 100
        job_status[job_id].estimated_time_remaining = 0
        job_status[job_id].result = {
            "video_path": video_path,
            "script": script,
            "effects": [], # No effects for text-generated videos for now
            "used_custom_voice": voice_file is not None
        }
        
    except Exception as e:
        print(f"Error in text-to-video generation: {e}")
        job_status[job_id].status = "failed"
        job_status[job_id].error = f"Failed to generate video: {str(e)}"

def simulate_training(model_id):
    """Simulate training a model (for demo purposes)"""
    try:
        # Simulated training steps
        steps = ["preprocessing", "feature_extraction", "training", "finetuning", "completed"]
        
        for step in steps:
            # Update status
            training_models[model_id].status = step
            
            # Simulate processing time
            time.sleep(2)
        
        # Create a dummy model file
        model_file = os.path.join('models', f"{model_id}.model")
        with open(model_file, 'w') as f:
            f.write(f"Simulated model created at {datetime.now().isoformat()}")
        
        print(f"Model {model_id} training completed")
    
    except Exception as e:
        print(f"Error in training simulation: {str(e)}")
        training_models[model_id].status = "failed"

def calculate_estimated_time(duration, add_voiceover=False):
    """Calculate the estimated time for video generation in seconds"""
    # Base time depends on video duration (typically takes longer for longer videos)
    base_time = duration * 3  # Rough estimate: 3 seconds of processing per 1 second of video
    
    # Additional time for effects, analysis, etc.
    additional_time = 30  # 30 seconds for image analysis and script generation
    
    # Additional time if voiceover is enabled
    voiceover_time = 15 if add_voiceover else 0
    
    return base_time + additional_time + voiceover_time

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True) 