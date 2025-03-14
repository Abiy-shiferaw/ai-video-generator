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
import random
from threading import Thread
import math
import traceback

# Add Eleven Labs import
import requests as elevenlabs_requests  # Using requests for Eleven Labs API

# Import our new modules
from video_services import VideoGenerationService
from video_effects import AdvancedVideoEffects
from text_processing import TextProcessor
from video_optimizer import VideoOptimizer

# Add this import at the top of app.py, after other imports
import video_effects  # This will register our custom slide_in effect

# Import our VideoEnhancer
from video_enhancer import VideoEnhancer

# Import ContentAnalyzer and VideoRecommender
from content_analyzer import ContentAnalyzer
from video_recommender import VideoRecommender

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

# Initialize dictionaries to track jobs
job_status = {}
video_jobs = {}
training_jobs = {}

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

def update_estimated_time(job_data, current_progress):
    """
    Update the estimated time remaining based on elapsed time and progress
    
    Args:
        job_data: The current job status dictionary
        current_progress: The current progress percentage
        
    Returns:
        Updated estimated time remaining in seconds
    """
    # If there's no start time, return the original estimate
    if "started_at" not in job_data or not job_data["started_at"]:
        return job_data.get("estimated_time_remaining", 60)  # Default to 60 seconds if not set
        
    # Calculate elapsed time
    elapsed_time = time.time() - job_data["started_at"]
    
    # If progress is very low, return the original estimate
    if current_progress < 10:
        return job_data.get("estimated_time_remaining", 60)
        
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
            {"method": "GET", "url": "/api/status/<job_id>", "description": "Check job status"},
            {"method": "POST", "url": "/api/generate-video-from-text", "description": "Generate video from text prompt"},
            {"method": "POST", "url": "/api/generate-ad", "description": "Generate professional advertisement"},
            {"method": "POST", "url": "/api/generate-advanced-video", "description": "Generate advanced motion video with AI"}
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
def check_job_status(job_id):
    """Check the status of a job"""
    # Check in job_status dictionary first
    if job_id in job_status:
        return jsonify({
            "status": job_status[job_id]["status"],
            "progress": job_status[job_id]["progress"],
            "estimated_time_remaining": job_status[job_id].get("estimated_time_remaining"),
            "result": job_status[job_id].get("result"),
            "error": job_status[job_id].get("error")
        })
    
    # If not found, check in video_jobs dictionary
    if job_id in video_jobs:
        return jsonify({
            "status": video_jobs[job_id]["status"],
            "progress": video_jobs[job_id]["progress"],
            "estimated_time_remaining": video_jobs[job_id].get("estimated_time_remaining"),
            "result": video_jobs[job_id].get("result"),
            "error": video_jobs[job_id].get("error")
        })
    
    # If not found in either dictionary, return a 404 error
    return jsonify({
        "status": "not_found",
        "error": "Job not found"
    }), 404

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

@app.route('/api/download/<path:filepath>', methods=['GET'])
def download_file(filepath):
    """Download a generated video file with support for nested paths"""
    try:
        print(f"Request to download: {filepath}")
        # Check if the path is directly inside OUTPUT_FOLDER
        full_path = os.path.join(app.config['OUTPUT_FOLDER'], filepath)
        
        # If not there, check if it's a full path relative to project root
        if not os.path.exists(full_path) and filepath.startswith(app.config['OUTPUT_FOLDER']):
            full_path = filepath
        
        print(f"Looking for file at: {full_path}")
        if not os.path.exists(full_path):
            # Try another option - we might have received a full path
            if os.path.exists(filepath):
                full_path = filepath
            else:
                print(f"File not found at {full_path}")
                return jsonify({"error": "File not found"}), 404
        
        # Get the directory and filename
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        
        return send_from_directory(directory, filename, as_attachment=True)
    except Exception as e:
        print(f"Error during download: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload-voice', methods=['POST'])
def upload_voice():
    """Upload a voice file for use in video generation"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"})
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"})
        
    if file and allowed_file(file.filename, ['mp3', 'wav']):
        # Save the file
        voice_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'voices')
        os.makedirs(voice_dir, exist_ok=True)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(voice_dir, filename)
        file.save(filepath)
        
        return jsonify({
            "success": True,
            "message": "Voice file uploaded successfully",
            "filename": filename,
            "filepath": filepath
        })
    else:
        return jsonify({"success": False, "error": "File type not allowed"})

@app.route('/api/clone-voice', methods=['POST'])
def clone_voice():
    """Clone a voice using ElevenLabs API"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"})
            
        voice_sample_path = data.get('voice_sample_path')
        voice_name = data.get('voice_name', 'Custom Voice')
        description = data.get('description', 'Custom cloned voice')
        
        if not voice_sample_path or not os.path.exists(voice_sample_path):
            return jsonify({"success": False, "error": "Voice sample file not found"})
            
        # Check if we have an ElevenLabs API key
        if not ELEVEN_LABS_API_KEY:
            return jsonify({"success": False, "error": "ElevenLabs API key not configured"})
            
        # Prepare the request data for voice cloning
        headers = {
            "xi-api-key": ELEVEN_LABS_API_KEY,
            "Accept": "application/json"
        }
        
        # First, create a new voice
        voice_data = {
            "name": voice_name,
            "description": description,
            "labels": {"accent": "custom"}
        }
        
        # Create the voice
        create_response = elevenlabs_requests.post(
            "https://api.elevenlabs.io/v1/voices/add",
            headers=headers,
            json=voice_data
        )
        
        if create_response.status_code != 200:
            return jsonify({
                "success": False, 
                "error": f"Failed to create voice: {create_response.text}"
            })
            
        # Get the voice ID from the response
        voice_id = create_response.json().get("voice_id")
        
        if not voice_id:
            return jsonify({
                "success": False,
                "error": "Failed to get voice ID from response"
            })
            
        # Now, add the voice sample to train the model
        with open(voice_sample_path, 'rb') as f:
            files = {'files': (os.path.basename(voice_sample_path), f, 'audio/mpeg')}
            
            add_sample_response = elevenlabs_requests.post(
                f"https://api.elevenlabs.io/v1/voices/{voice_id}/edit/add",
                headers={"xi-api-key": ELEVEN_LABS_API_KEY},
                files=files
            )
            
        if add_sample_response.status_code != 200:
            return jsonify({
                "success": False,
                "error": f"Failed to add voice sample: {add_sample_response.text}"
            })
            
        # Store the cloned voice in our database
        # Add to our custom voices collection
        custom_voice = {
            "voice_id": voice_id,
            "name": voice_name,
            "category": "custom",
            "gender": "custom",
            "preview_url": f"/api/voices/{os.path.basename(voice_sample_path)}",
            "description": description,
            "is_cloned": True
        }
        
        # Save this info to a file for persistence
        cloned_voices_file = os.path.join(app.config['UPLOAD_FOLDER'], 'cloned_voices.json')
        cloned_voices = []
        
        if os.path.exists(cloned_voices_file):
            try:
                with open(cloned_voices_file, 'r') as f:
                    cloned_voices = json.load(f)
            except:
                cloned_voices = []
                
        cloned_voices.append(custom_voice)
        
        with open(cloned_voices_file, 'w') as f:
            json.dump(cloned_voices, f)
        
        return jsonify({
            "success": True,
            "message": "Voice cloned successfully",
            "voice_id": voice_id,
            "voice_name": voice_name
        })
        
    except Exception as e:
        print(f"Error cloning voice: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/voices/<filename>', methods=['GET'])
def get_voice(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/voices/available', methods=['GET'])
def get_available_voices():
    """Return a list of available voices for text-to-speech"""
    try:
        # Define default ElevenLabs voices
        elevenlabs_voices = [
            {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "name": "Rachel",
                "category": "professional",
                "gender": "female",
                "preview_url": "",
                "description": "A professional female voice with a warm and clear delivery."
            },
            {
                "voice_id": "AZnzlk1XvdvUeBnXmlld",
                "name": "Domi",
                "category": "professional",
                "gender": "male",
                "preview_url": "",
                "description": "A professional male voice with an assertive and confident tone."
            },
            {
                "voice_id": "EXAVITQu4vr4xnSDxMaL",
                "name": "Bella",
                "category": "professional",
                "gender": "female",
                "preview_url": "",
                "description": "A friendly and approachable female voice."
            },
            {
                "voice_id": "VR6AewLTigWG4xSOukaG",
                "name": "Adam",
                "category": "professional",
                "gender": "male",
                "preview_url": "",
                "description": "A deep authoritative male voice."
            },
            {
                "voice_id": "pNInz6obpgDQGcFmaJgB",
                "name": "Sam",
                "category": "casual",
                "gender": "male",
                "preview_url": "",
                "description": "A casual and conversational male voice."
            },
            {
                "voice_id": "yoZ06aMxZJJ28mfd3POQ",
                "name": "Emily",
                "category": "casual",
                "gender": "female",
                "preview_url": "",
                "description": "A friendly and approachable female voice, perfect for explanations."
            },
            # Adding more professional voices
            {
                "voice_id": "jBpfuIE2acCO8z3wKNLl",
                "name": "Michael",
                "category": "professional",
                "gender": "male",
                "preview_url": "",
                "description": "A mature, authoritative male voice with excellent enunciation."
            },
            {
                "voice_id": "SOYHLrjzK2CQxersoZHG",
                "name": "Charlotte",
                "category": "professional",
                "gender": "female",
                "preview_url": "",
                "description": "A confident, articulate female voice with a British accent."
            },
            {
                "voice_id": "XB0fDUnXU5powFXDhCwa",
                "name": "Thomas",
                "category": "professional",
                "gender": "male",
                "preview_url": "",
                "description": "A friendly, trustworthy male voice with natural cadence."
            },
            {
                "voice_id": "flq6f7yk4E4fJM5XTYuZ",
                "name": "Sophia",
                "category": "professional",
                "gender": "female",
                "preview_url": "",
                "description": "A warm, conversational female voice that sounds genuine and approachable."
            }
        ]
        
        # Get custom voices from uploads folder
        custom_voices = []
        voice_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'voices')
        if os.path.exists(voice_folder):
            for file in os.listdir(voice_folder):
                if file.endswith(('.mp3', '.wav')):
                    voice_id = 'custom-' + os.path.splitext(file)[0]
                    name = os.path.splitext(file)[0].replace('_', ' ').title()
                    custom_voices.append({
                        "voice_id": voice_id,
                        "name": f"Custom: {name}",
                        "category": "custom",
                        "gender": "unknown",
                        "preview_url": f"/api/voices/voices/{file}",
                        "description": "Your custom uploaded voice."
                    })
        
        # Get cloned voices from the JSON file
        cloned_voices = []
        cloned_voices_file = os.path.join(app.config['UPLOAD_FOLDER'], 'cloned_voices.json')
        if os.path.exists(cloned_voices_file):
            try:
                with open(cloned_voices_file, 'r') as f:
                    cloned_voices = json.load(f)
            except Exception as e:
                print(f"Error loading cloned voices: {str(e)}")
        
        # Fetch additional voices from ElevenLabs API if available
        if ELEVEN_LABS_API_KEY:
            try:
                headers = {
                    "xi-api-key": ELEVEN_LABS_API_KEY,
                    "Accept": "application/json"
                }
                
                response = elevenlabs_requests.get(
                    "https://api.elevenlabs.io/v1/voices",
                    headers=headers
                )
                
                if response.status_code == 200:
                    api_voices = response.json().get("voices", [])
                    
                    # Filter out voices that are already in our list
                    existing_voice_ids = [v["voice_id"] for v in elevenlabs_voices]
                    
                    for voice in api_voices:
                        if voice["voice_id"] not in existing_voice_ids:
                            # Determine category based on labels or default to "other"
                            category = "other"
                            
                            # Extract labels if they exist
                            labels = voice.get("labels", {})
                            
                            if "professional" in labels.values():
                                category = "professional"
                            elif "casual" in labels.values():
                                category = "casual"
                            elif labels.get("accent") == "custom":
                                category = "custom"
                                
                            # Add to our voices list
                            elevenlabs_voices.append({
                                "voice_id": voice["voice_id"],
                                "name": voice["name"],
                                "category": category,
                                "gender": labels.get("gender", "unknown"),
                                "preview_url": voice.get("preview_url", ""),
                                "description": voice.get("description", "Voice from ElevenLabs.")
                            })
            except Exception as e:
                print(f"Error fetching voices from ElevenLabs: {str(e)}")
        
        # Combine all voices
        all_voices = elevenlabs_voices + custom_voices + cloned_voices
        
        return jsonify({
            "success": True,
            "voices": all_voices
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

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

# Initialize animation style templates
ANIMATION_STYLES = {
    "sleek": "Sleek and smooth professional animations with clean transitions",
    "motion": "Dynamic motion graphics with modern design elements",
    "isometric": "3D isometric animations with depth and perspective",
    "2d": "2D character animations with personality and movement",
    "infographic": "Data-driven infographic animations that visualize information clearly"
}

# Initialize color schemes for ads
COLOR_SCHEMES = {
    "blue": {"primary": "#0062cc", "secondary": "#4e95f4", "accent": "#001f3f", "background": "#f5f9ff"},
    "teal": {"primary": "#00b8a9", "secondary": "#7ae7df", "accent": "#005f56", "background": "#f0fffd"},
    "purple": {"primary": "#7209b7", "secondary": "#b39cd0", "accent": "#3a0068", "background": "#f9f0ff"},
    "red": {"primary": "#e71d36", "secondary": "#ff9f93", "accent": "#7a0921", "background": "#fff5f5"},
    "dark": {"primary": "#2d3436", "secondary": "#636e72", "accent": "#0984e3", "background": "#1e272e"},
    "pastel": {"primary": "#fdcb6e", "secondary": "#55efc4", "accent": "#fd79a8", "background": "#ffeaa7"}
}

# Advertising templates
AD_TEMPLATES = {
    "product": "Product showcase focusing on features and benefits",
    "testimonial": "Customer testimonial highlighting positive experiences",
    "explainer": "Educational explanation of how a product or service works",
    "storytelling": "Narrative-driven ad that tells a compelling story",
    "corporate": "Professional corporate messaging with brand emphasis"
}

@app.route('/api/generate-ad', methods=['POST'])
def create_ad():
    """Generate a professional animated advertisement"""
    data = request.json
    
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400
    
    # Extract data - look for both 'prompt' and 'ad_text' to be compatible with different frontends
    prompt = data.get('prompt') or data.get('ad_text')
    if not prompt:
        return jsonify({"success": False, "error": "No ad content provided"}), 400
    
    brand_name = data.get('brand_name', '')
    tagline = data.get('tagline', '')
    target_audience = data.get('target_audience', '')
    duration = data.get('duration', 30)
    style = data.get('style', 'professional')
    template = data.get('template', 'product')
    color_scheme = data.get('color_scheme', 'blue')
    animation_style = data.get('animation_style', 'sleek')
    voice_id = data.get('voice_id')
    
    print(f"Received ad generation request: {data}")
    
    # Format for color palette
    colors = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES['blue'])
    
    # Prepare voice file if provided
    voice_file = None
    if voice_id:
        voice_files = [f for f in os.listdir('voices') if voice_id in f]
        if voice_files:
            voice_file = os.path.join('voices', voice_files[0])
    
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
        target=process_ad_generation,
        args=(job_id, prompt, brand_name, tagline, target_audience, duration, style, template, color_scheme, animation_style, voice_file)
    )
    process_thread.daemon = True
    process_thread.start()
    
    return jsonify({
        "success": True,
        "job_id": job_id,
        "status": "processing"
    }), 200

def parse_timing(timing_str):
    """
    Parse a timing string and convert it to seconds (float).
    Handles formats like:
    - "5" (already a number)
    - "5 seconds"
    - "0-3 seconds" (takes the average)
    - "2.5s"
    """
    try:
        # If it's already a number, return it
        if isinstance(timing_str, (int, float)):
            return float(timing_str)
        
        # Remove 'seconds' or 's' suffix
        timing_str = timing_str.lower().replace('seconds', '').replace('s', '').strip()
        
        # Check if it's a range (e.g., "0-3")
        if '-' in timing_str:
            parts = timing_str.split('-')
            start = float(parts[0].strip())
            end = float(parts[1].strip())
            return (start + end) / 2  # Use the average of the range
        
        # Otherwise, convert to float
        return float(timing_str)
    except Exception as e:
        print(f"Error parsing timing string '{timing_str}': {str(e)}")
        # Default to 3 seconds if we can't parse
        return 3.0

def process_ad_generation(job_id, prompt, brand_name, tagline, target_audience, 
                         duration, style, template, color_scheme, animation_style, voice_file=None):
    """Process ad generation in the background"""
    try:
        # Update job status to 10%
        job_status[job_id].progress = 10
        job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 10)
        
        # 1. Generate ad script using OpenAI
        system_prompt = f"""You are an expert advertising copywriter and storyboard artist.
Create a professional {duration}-second ad for a brand called "{brand_name}".
Tagline: "{tagline}"
Target audience: {target_audience}
Style: {style}
Template: {AD_TEMPLATES.get(template, AD_TEMPLATES['product'])}
Animation style: {ANIMATION_STYLES.get(animation_style, ANIMATION_STYLES['sleek'])}
Color scheme: {color_scheme.capitalize()} (Primary: {COLOR_SCHEMES[color_scheme]['primary']}, Secondary: {COLOR_SCHEMES[color_scheme]['secondary']})

Create a detailed storyboard with:
1. Scene-by-scene description
2. Visual elements and animations for each scene
3. Timing for each scene (total must be {duration} seconds)
4. Text overlays and transitions
5. Voice-over script that matches the ad visuals

Format as a JSON object with these fields:
- scenes: Array of scenes with {{"timing": "seconds", "description": "visual description", "animation": "animation details", "voiceover": "script"}}
- brand_elements: Array of brand elements to include
- text_overlays: Array of text to display with timing
- music_suggestion: Type of background music that fits
"""

        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the JSON content from the response
        script_content = response.choices[0].message.content
        
        # Clean up the response to extract just the JSON part
        if "```json" in script_content:
            script_content = script_content.split("```json")[1].split("```")[0].strip()
        elif "```" in script_content:
            script_content = script_content.split("```")[1].split("```")[0].strip()
            
        ad_script = json.loads(script_content)
        
        # Update job status to 30%
        job_status[job_id].progress = 30
        job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 30)
        
        # 2. Generate animation scenes using visual prompts
        scenes = []
        for i, scene in enumerate(ad_script["scenes"]):
            # Generate scene visuals using DALL-E
            scene_prompt = f"""Create a professional {style} advertisement visual for {brand_name}.
Scene description: {scene['description']}
Animation style: {ANIMATION_STYLES.get(animation_style, ANIMATION_STYLES['sleek'])}
Color scheme: Primary {COLOR_SCHEMES[color_scheme]['primary']}, Secondary {COLOR_SCHEMES[color_scheme]['secondary']}
Make it high quality, professional, and NOT AI-generated looking. Create a clean, professional ad frame.
"""
            
            # Use DALL-E to generate scene image
            try:
                dalle_response = openai.images.generate(
                    model="dall-e-3",
                    prompt=scene_prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1
                )
                
                # Save the generated image
                image_url = dalle_response.data[0].url
                image_data = requests.get(image_url).content
                
                # Create scene folder
                scene_folder = os.path.join('temp', job_id)
                os.makedirs(scene_folder, exist_ok=True)
                
                # Save image
                image_path = os.path.join(scene_folder, f"scene_{i+1}.png")
                with open(image_path, 'wb') as img_file:
                    img_file.write(image_data)
                    
                # Add to scenes list
                scenes.append({
                    "path": image_path,
                    "duration": parse_timing(scene["timing"]),
                    "voiceover": scene["voiceover"],
                    "animation": scene["animation"]
                })
                
                # Update progress (scenes are 30% to 70% of progress)
                progress = 30 + int(40 * (i + 1) / len(ad_script["scenes"]))
                job_status[job_id].progress = progress
                job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], progress)
                
            except Exception as e:
                print(f"Error generating scene {i+1}: {str(e)}")
                job_status[job_id].status = "failed"
                job_status[job_id].error = f"Failed to generate scene {i+1}: {str(e)}"
                return
        
        # 3. Generate voiceover audio
        audio_path = None
        if voice_file:
            # Combine all voiceover text
            voiceover_text = " ".join([scene["voiceover"] for scene in ad_script["scenes"]])
            
            try:
                temp_audio_path = os.path.join('temp', job_id, "voiceover.mp3")
                
                # Initialize voice_id
                voice_id = "EXAVITQu4vr4xnSDxMaL"  # Default Eleven Labs voice ID (professional male)
                
                # If voice_file is provided, try to get or create a voice
                if voice_file and os.path.exists(voice_file):
                    try:
                        # Extract voice name from file
                        voice_name = os.path.basename(voice_file).split('.')[0]
                        
                        # Check for existing voice
                        headers = {"xi-api-key": ELEVEN_LABS_API_KEY}
                        response = elevenlabs_requests.get(
                            "https://api.elevenlabs.io/v1/voices",
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            voices = response.json().get("voices", [])
                            # Check if we already have this voice
                            for v in voices:
                                if v["name"] == voice_name:
                                    voice_id = v["voice_id"]
                                    print(f"Using existing voice ID: {voice_id}")
                                    break
                        
                            # If not found, create a new voice
                            if voice_id == "EXAVITQu4vr4xnSDxMaL":  # Still using default
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
                    except Exception as e:
                        print(f"Error getting/creating voice: {str(e)}")
                        # Continue with default voice
                
                # Try to use Eleven Labs for voice generation
                headers = {
                    "xi-api-key": ELEVEN_LABS_API_KEY,
                    "Content-Type": "application/json"
                }
                
                # Use the voice ID to generate TTS
                data = {
                    "text": voiceover_text,
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
                    with open(temp_audio_path, "wb") as f:
                        f.write(response.content)
                    audio_path = temp_audio_path
                    print(f"Generated TTS audio using Eleven Labs: {audio_path}")
                else:
                    print(f"Error generating speech with Eleven Labs: {response.text}")
                    # Fall back to Google TTS
                    tts = gtts.gTTS(text=voiceover_text, lang="en", slow=False)
                    tts.save(temp_audio_path)
                    audio_path = temp_audio_path
            except Exception as e:
                print(f"Error generating voiceover: {str(e)}")
                # Fall back to Google TTS
                try:
                    temp_audio_path = os.path.join('temp', job_id, "voiceover.mp3")
                    tts = gtts.gTTS(text=voiceover_text, lang="en", slow=False)
                    tts.save(temp_audio_path)
                    audio_path = temp_audio_path
                except Exception as audio_err:
                    print(f"Error generating fallback audio: {str(audio_err)}")
        
        # Update progress to 80%
        job_status[job_id].progress = 80
        job_status[job_id].estimated_time_remaining = update_estimated_time(job_status[job_id], 80)
        
        # 4. Create the animated video using MoviePy
        try:
            # Create temp folder for output
            output_folder = os.path.join(OUTPUT_FOLDER, job_id)
            os.makedirs(output_folder, exist_ok=True)
            
            output_path = os.path.join(output_folder, f"ad_{job_id}.mp4")
            
            # Create video clips for each scene
            video_clips = []
            for scene in scenes:
                # Create image clip
                img_clip = ImageClip(scene["path"]).set_duration(scene["duration"])
                
                # Apply animation effects based on description
                animation_desc = scene["animation"].lower()
                
                if "zoom" in animation_desc:
                    img_clip = img_clip.fx(vfx.resize, lambda t: 1 + 0.05 * t)
                
                if "fade in" in animation_desc:
                    img_clip = img_clip.fx(vfx.fadein, 0.5)
                
                if "fade out" in animation_desc:
                    img_clip = img_clip.fx(vfx.fadeout, 0.5)
                
                if "slide" in animation_desc:
                    img_clip = img_clip.fx(vfx.slide_in, 0.5, 'left')
                
                # Add texts from the ad_script if they match this scene's timing
                text_clips = []
                for text_overlay in ad_script.get("text_overlays", []):
                    if text_overlay.get("scene") == scenes.index(scene) + 1:
                        txt = TextClip(
                            text_overlay.get("text", ""), 
                            fontsize=text_overlay.get("size", 40), 
                            color=text_overlay.get("color", "white"), 
                            font=text_overlay.get("font", "Arial-Bold"),
                            stroke_color=text_overlay.get("stroke_color", "black"),
                            stroke_width=text_overlay.get("stroke_width", 1)
                        )
                        
                        txt = txt.set_position(text_overlay.get("position", "center"))
                        txt = txt.set_duration(scene["duration"])
                        
                        if "fade" in text_overlay.get("animation", "").lower():
                            txt = txt.fadein(0.5).fadeout(0.5)
                            
                        text_clips.append(txt)
                
                # If there are text clips, compose them with the image clip
                if text_clips:
                    scene_clip = CompositeVideoClip([img_clip] + text_clips)
                    scene_clip = scene_clip.set_duration(img_clip.duration)
                else:
                    scene_clip = img_clip
                
                video_clips.append(scene_clip)
            
            # Concatenate all clips
            final_clip = concatenate_videoclips(video_clips, method="compose")
            
            # Add audio if available
            if audio_path:
                audio = AudioFileClip(audio_path)
                final_clip = final_clip.set_audio(audio)
            
            # Write the final video
            final_clip.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast"
            )
            
            # Update job status to completed
            job_status[job_id].status = "completed"
            job_status[job_id].progress = 100
            job_status[job_id].estimated_time_remaining = 0
            
            # Store the relative path for easier frontend access
            relative_path = output_path
            if output_path.startswith(app.config['OUTPUT_FOLDER']):
                # If the path starts with OUTPUT_FOLDER, remove that prefix to make it relative
                relative_path = output_path[len(app.config['OUTPUT_FOLDER']):].lstrip('/')
                # Ensure the path format is consistent
                relative_path = f"{job_id}/ad_{job_id}.mp4"
            
            job_status[job_id].result = {
                "video_path": relative_path,
                "script": ad_script,
                "used_custom_voice": voice_file is not None,
                "brand_name": brand_name,
                "tagline": tagline,
                "ad_template": template,
                "ad_style": style,
                "animation_style": animation_style
            }
            
        except Exception as e:
            print(f"Error creating video: {str(e)}")
            job_status[job_id].status = "failed"
            job_status[job_id].error = f"Failed to create video: {str(e)}"
            return
        
    except Exception as e:
        print(f"Error in ad generation: {str(e)}")
        job_status[job_id].status = "failed"
        job_status[job_id].error = f"Error in ad generation: {str(e)}"

def generate_testimonial_script(prompt, duration=45):
    """Generate a structured script for testimonial videos to improve lip sync"""
    try:
        # Use OpenAI to create a testimonial script
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        system_message = """
        You are an expert at creating natural-sounding testimonial scripts for business videos.
        Create a 45-second testimonial script that sounds authentic and conversational.
        The script should be written from the first-person perspective as if the business owner is speaking.
        Focus on:
        1. Introducing the business in the first 15 seconds
        2. Highlighting key services/benefits in the middle
        3. A strong call to action at the end
        Keep sentences short and natural for better lip sync.
        """
        
        prompt_with_instructions = f"""
        Create a conversational testimonial script for this business: {prompt}
        
        Make it about {duration} seconds when read naturally.
        Use natural, simple language that would work well for lip syncing.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt_with_instructions}
            ],
            max_tokens=500
        )
        
        script = response.choices[0].message.content.strip()
        return {"success": True, "script": script}
    except Exception as e:
        print(f"Error generating testimonial script: {str(e)}")
        return {"success": False, "error": str(e), "script": f"Hi, I'm a professional in the field. {prompt[:100]}..."}

@app.route('/api/generate-advanced-video', methods=['POST'])
def generate_advanced_video():
    """
    Endpoint to generate an advanced video with AI from text prompt
    """
    try:
        data = request.json
        
        # Get the prompt and parameters
        prompt = data.get('prompt')
        style = data.get('style', 'realistic')
        duration = int(data.get('duration', 30))
        video_source = data.get('video_source', 'default')
        add_voiceover = data.get('add_voiceover', False)
        voice_id = data.get('voice_id', None)
        
        # Check if we have a prompt
        if not prompt:
            return jsonify({
                "success": False,
                "error": "No prompt provided"
            })
        
        # Generate a job ID
        job_id = f"adv_vid_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Create the job directory
        output_dir = f"output/{job_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Store job status
        video_jobs[job_id] = {
            "status": "processing",
            "progress": 0,
            "output_file": None,
            "error": None
        }
        
        # Process the job in a background thread
        Thread(target=process_advanced_video_job, args=(job_id, prompt, style, duration, video_source, add_voiceover, voice_id)).start()
        
        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": "Video generation job started"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

def generate_eleven_labs_tts(text, voice_id, output_path):
    """
    Generate text-to-speech audio using Eleven Labs API
    
    Args:
        text (str): The text to convert to speech
        voice_id (str): The Eleven Labs voice ID to use
        output_path (str): Path to save the generated audio
        
    Returns:
        dict: Result with success status and path or error
    """
    try:
        print(f"Generating TTS with Eleven Labs using voice ID: {voice_id}")
        
        # Make sure the output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Set up the API request
        headers = {
            "xi-api-key": ELEVEN_LABS_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Prepare the request data
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        # Make the API request
        response = elevenlabs_requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers=headers,
            json=data
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            # Save the audio file
            with open(output_path, "wb") as f:
                f.write(response.content)
            return {"success": True, "audio_path": output_path}
        else:
            error_msg = f"Error from Eleven Labs API: {response.text}"
            print(error_msg)
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"Failed to generate TTS with Eleven Labs: {str(e)}"
        print(error_msg)
        return {"success": False, "error": error_msg}

def process_advanced_video_job(job_id, prompt, style, duration, video_source, add_voiceover, voice_id):
    """Process an advanced video generation job in the background"""
    # Create a unique output directory for this job
    timestamp = int(time.time())
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], f'advanced_{job_id}_{timestamp}')
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Initialize job in global dictionary
        if job_id not in video_jobs:
            video_jobs[job_id] = {
                "status": "initializing",
                "progress": 0,
                "started_at": time.time(),
                "estimated_time_remaining": calculate_estimated_time(int(duration), add_voiceover)
            }
        
        # Update job status to script generation
        video_jobs[job_id]["status"] = "generating_script"
        video_jobs[job_id]["progress"] = 10
        video_jobs[job_id]["estimated_time_remaining"] = update_estimated_time(video_jobs[job_id], 10)
        
        # Base path for the output video
        video_path = f"{output_dir}/generated_video.mp4"
        
        # Get content type (testimonial, commercial, etc)
        content_analyzer = ContentAnalyzer()
        content_type = content_analyzer.detect_content_type(prompt)
        
        # Store detected content type for enhancements
        primary_video_type = content_type["primary_type"]
        print(f"Detected content type: {primary_video_type}")
        
        # Determine if we need to optimize duration based on content
        optimizer = VideoOptimizer()
        optimized_duration = optimizer.recommend_duration(prompt, int(duration))
        optimized_style = optimizer.recommend_style(prompt, style)
        
        # Determine recommended video source if not specified
        recommended_source = video_source
        if not video_source:
            recommended_source = VideoRecommender.recommend_source(prompt, primary_video_type)
            print(f"Recommended video source: {recommended_source}")
        
        # Generate voiceover text for the video
        voiceover_text = ""
        
        # Update progress for script generation
        video_jobs[job_id]["progress"] = 20
        video_jobs[job_id]["estimated_time_remaining"] = update_estimated_time(video_jobs[job_id], 20)
        
        # Generate appropriate script based on content type
        if primary_video_type == "testimonial":
            # Generate a testimonial script
            print("Generating testimonial script...")
            script_result = generate_testimonial_script(prompt, optimized_duration)
            if script_result["success"]:
                voiceover_text = script_result["script"]
                print(f"Generated testimonial script: {voiceover_text[:100]}...")
        
        # Determine if hybrid approach is recommended (if not explicitly specified)
        should_use_hybrid = video_source and video_source.lower() == 'hybrid'
        if not video_source:
            should_use_hybrid = VideoOptimizer.should_use_hybrid_approach(prompt, optimized_duration)
            if should_use_hybrid:
                print("Automatically selected hybrid approach based on content analysis")
                recommended_source = "hybrid"
        
        # Update progress for video generation starting
        video_jobs[job_id]["status"] = "generating_video"
        video_jobs[job_id]["progress"] = 30
        video_jobs[job_id]["estimated_time_remaining"] = update_estimated_time(video_jobs[job_id], 30)
        
        # Generate the video
        if recommended_source and recommended_source.lower() == 'hybrid':
            # Generate a hybrid video (stock + AI)
            video_result = VideoGenerationService.generate_hybrid_video(
                prompt=prompt,
                duration=float(optimized_duration),
                style=optimized_style,
                output_path=video_path
            )
        else:
            # Generate video using specified source or default approach
            video_result = VideoGenerationService.generate_video_from_text(
                prompt=prompt,
                style=optimized_style,
                duration=float(optimized_duration),
                output_path=video_path,
                video_source=recommended_source
            )
            
        # Update progress after video generation
        video_jobs[job_id]["progress"] = 50
        video_jobs[job_id]["estimated_time_remaining"] = update_estimated_time(video_jobs[job_id], 50)
        
        # Check if video generation was successful
        final_video_path = video_path
        if video_result:
            # Get the path to the generated video
            if isinstance(video_result, str):
                generated_video_path = video_result
            elif isinstance(video_result, dict) and video_result.get("success") and video_result.get("video_path"):
                generated_video_path = video_result["video_path"]
            elif isinstance(video_result, dict) and video_result.get("success") and video_result.get("output_path"):
                generated_video_path = video_result["output_path"]
            else:
                raise Exception(f"Video generation failed: {video_result}")
                
            video_jobs[job_id]["progress"] = 60
            video_jobs[job_id]["status"] = "enhancing_video"
            video_jobs[job_id]["estimated_time_remaining"] = update_estimated_time(video_jobs[job_id], 60)
            
            # Apply video enhancements based on detected content type
            enhanced_video_path = f"{output_dir}/enhanced_{os.path.basename(generated_video_path)}"
            
            # Determine enhancement parameters based on video type
            apply_smoothing = True
            enhance_objects = True
            enhancement_style = primary_video_type
            
            if primary_video_type == "testimonial":
                # Testimonials need different enhancements
                frame_rate = 24  # Film-like frame rate for testimonials
            elif primary_video_type == "commercial":
                frame_rate = 30  # Higher frame rate for commercial content
            elif primary_video_type == "cinematic":
                frame_rate = 24  # Film-like frame rate for cinematic content
            else:
                frame_rate = 30  # Default
                
            print(f"Applying video enhancements with style: {enhancement_style}, frame rate: {frame_rate}")
            
            # Apply the enhancements
            enhanced_video_path = VideoEnhancer.process_video(
                input_path=generated_video_path,
                output_path=enhanced_video_path,
                apply_smoothing=apply_smoothing,
                enhance_objects=enhance_objects,
                style=enhancement_style,
                frame_rate=frame_rate
            )
            
            # Update job progress
            video_jobs[job_id]["progress"] = 70
            video_jobs[job_id]["status"] = "processing_audio"
            video_jobs[job_id]["estimated_time_remaining"] = update_estimated_time(video_jobs[job_id], 70)
            
            final_video_path = enhanced_video_path
            
            # Update output file in job status
            video_jobs[job_id]["output_file"] = os.path.basename(final_video_path)
        
        # Add voice-over if requested
        if add_voiceover and voice_id:
            try:
                video_jobs[job_id]["status"] = "adding_voiceover"
                video_jobs[job_id]["progress"] = 80
                video_jobs[job_id]["estimated_time_remaining"] = update_estimated_time(video_jobs[job_id], 80)
                
                # Generate voice-over audio
                audio_path = f"{output_dir}/narration.mp3"
                
                print(f"Generating voice with ElevenLabs using voice ID: {voice_id}")
                tts_result = generate_eleven_labs_tts(voiceover_text, voice_id, audio_path)
                
                if tts_result.get('success'):
                    print(f"Generated TTS audio using Eleven Labs: {audio_path}")
                    
                    # Add voice-over to video
                    from moviepy.editor import VideoFileClip, AudioFileClip
                    import math
                    
                    # Create the output file name
                    final_output_path = f"{output_dir}/video_with_audio_{int(time.time())}.mp4"
                    
                    # Combine video and audio
                    video_clip = VideoFileClip(final_video_path)
                    audio_clip = AudioFileClip(audio_path)
                    
                    # Get durations
                    video_duration = video_clip.duration
                    audio_duration = audio_clip.duration
                    
                    print(f"Video duration: {video_duration}s, Audio duration: {audio_duration}s")
                    
                    # Handle sync based on durations
                    if abs(audio_duration - video_duration) > 1.0:  # If difference is more than 1 second
                        if audio_duration > video_duration:
                            # Audio is longer - extend video to match audio
                            print(f"Audio is longer than video by {audio_duration - video_duration}s. Extending video.")
                            # Loop the video to match audio duration with crossfade
                            from moviepy.video.fx.all import loop
                            video_clip = video_clip.fx(loop, duration=audio_duration)
                        else:
                            # Video is longer - either trim video or extend audio
                            print(f"Video is longer than audio by {video_duration - audio_duration}s.")
                            # Option 1: Trim video to match audio
                            # video_clip = video_clip.subclip(0, audio_duration)
                            
                            # Option 2: Extend audio by repeating to fill video (better for testimonials)
                            # Calculate how many times to loop
                            loop_times = math.ceil(video_duration / audio_duration)
                            print(f"Looping audio {loop_times} times to match video length")
                            if loop_times > 1:
                                # Create concatenated audio to match video length
                                from moviepy.audio.AudioClip import concatenate_audioclips
                                looped_audio = concatenate_audioclips([audio_clip] * loop_times)
                                # Trim to exact video duration
                                audio_clip = looped_audio.subclip(0, video_duration)
                    
                    # Set the audio to the video with a small fade in/out for smoother audio
                    audio_clip = audio_clip.audio_fadein(0.3).audio_fadeout(0.5)
                    final_clip = video_clip.set_audio(audio_clip)
                    
                    # Update progress to finalizing
                    video_jobs[job_id]["status"] = "finalizing"
                    video_jobs[job_id]["progress"] = 90
                    video_jobs[job_id]["estimated_time_remaining"] = update_estimated_time(video_jobs[job_id], 90)
                    
                    # Write the result to a file
                    final_clip.write_videofile(
                        final_output_path,
                        codec='libx264',
                        audio_codec='aac',
                        temp_audiofile=f"{output_dir}/temp_audio.m4a",
                        remove_temp=True
                    )
                    
                    # Update job status with the new file
                    video_jobs[job_id]["output_file"] = os.path.basename(final_output_path)
                else:
                    print(f"Failed to generate TTS: {tts_result.get('error')}")
            except Exception as e:
                print(f"Voice-over error: {str(e)}")
                # Don't set job to failed, just log the error and continue
                # The video will still be available without voiceover
                video_jobs[job_id]["error"] = f"Voiceover failed but video was generated: {str(e)}"
        
        # Update job status to completed
        video_jobs[job_id]["status"] = "completed"
        video_jobs[job_id]["progress"] = 100
        
        # Prepare result with additional information about the video
        video_jobs[job_id]["result"] = {
            "video_path": video_jobs[job_id]["output_file"],
            "full_path": os.path.join(output_dir, video_jobs[job_id]["output_file"]),
            "content_type": primary_video_type,
            "duration": optimized_duration,
            "used_hybrid": recommended_source and recommended_source.lower() == 'hybrid',
            "used_custom_voice": voice_id and 'custom' in voice_id.lower(),
            "output_dir": output_dir
        }
        
        print(f"Advanced video generation completed successfully: {video_jobs[job_id]['output_file']}")
        
    except Exception as e:
        error_message = f"Error in advanced video generation: {str(e)}"
        print(error_message)
        traceback.print_exc()
        
        # Update job status to failed
        if job_id in video_jobs:
            video_jobs[job_id]["status"] = "failed"
            video_jobs[job_id]["error"] = error_message

def generate_and_save_image(prompt, size="1024x1024"):
    """
    Generate an image using OpenAI's DALL-E and save it to disk
    
    Args:
        prompt (str): Text description of the image to generate
        size (str): Size of the image to generate (e.g., "1024x1024")
        
    Returns:
        str: Path to the saved image
    """
    try:
        # Create directory to save images
        os.makedirs('temp', exist_ok=True)
        
        # Generate image using OpenAI's DALL-E
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1
        )

        # Get the generated image URL
        image_url = response.data[0].url
        
        # Download the image
        image_data = requests.get(image_url).content
        
        # Save the image
        output_path = os.path.join("temp", f"image_{int(time.time())}.png")
        with open(output_path, 'wb') as f:
            f.write(image_data)
            
        return output_path
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        # Return a placeholder image if available, or raise the error
        placeholder_path = os.path.join("static", "placeholder.png")
        if os.path.exists(placeholder_path):
            return placeholder_path
        raise e

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True) 