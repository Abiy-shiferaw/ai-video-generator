import os
import requests
import json
import time
import random
from dotenv import load_dotenv
import base64
from typing import List, Dict, Any, Optional
import shutil
import urllib.parse
import re
import uuid

# Load environment variables
load_dotenv()

# Import our new TextProcessor
from text_processing import TextProcessor

# API Keys
RUNWAYML_API_KEY = os.getenv("RUNWAYML_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

class VideoGenerationService:
    """
    A service class for handling advanced video generation using various AI services
    """
    
    @staticmethod
    def generate_runway_video(prompt: str, duration: int = 4, **kwargs) -> Dict[str, Any]:
        """
        Generate a video using RunwayML's Gen-2 API
        
        Args:
            prompt (str): Text description of the video to generate
            duration (int): Duration in seconds (max 4 for RunwayML)
            
        Returns:
            dict: Result containing video URL or file path
        """
        if not RUNWAYML_API_KEY:
            print("ERROR: RunwayML API key not configured")
            return {"success": False, "error": "RunwayML API key not configured"}
        
        try:
            print(f"Starting RunwayML video generation with prompt: {prompt[:100]}...")
            
            # RunwayML Gen-2 has a max of 4 seconds per video
            actual_duration = min(duration, 4)
            
            # RunwayML API endpoint
            url = "https://api.runwayml.com/v1/inference"
            
            # Request headers
            headers = {
                "Authorization": f"Bearer {RUNWAYML_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Request body
            payload = {
                "model": "runway/gen-2",
                "input": {
                    "prompt": prompt,
                    "num_frames": actual_duration * 24,  # 24 FPS
                    "guidance_scale": kwargs.get("guidance_scale", 20),
                    "height": 576,
                    "width": 1024
                }
            }
            
            print(f"Sending request to RunwayML: {url}")
            print(f"Payload: {json.dumps(payload)}")
            
            # Make the request
            response = requests.post(url, headers=headers, json=payload)
            response_json = response.json()
            
            if response.status_code != 200 or "error" in response_json:
                error_detail = f"HTTP {response.status_code}: {response.text}"
                print(f"RunwayML API error: {error_detail}")
                return {
                    "success": False,
                    "error": f"RunwayML API error: {error_detail}"
                }
            
            print("RunwayML API request successful!")
            
            # Extract the video URL from the response
            video_url = response_json.get("output", {}).get("video", None)
            if not video_url:
                print(f"RunwayML did not return a video URL. Response: {response_json}")
                return {
                    "success": False,
                    "error": "RunwayML did not return a video URL"
                }
            
            print(f"Got video URL from RunwayML: {video_url}")
            
            # Download the video
            video_response = requests.get(video_url, stream=True)
            if video_response.status_code != 200:
                print(f"Failed to download video from RunwayML. HTTP {video_response.status_code}")
                return {
                    "success": False,
                    "error": f"Failed to download video: HTTP {video_response.status_code}"
                }
            
            # Save the video to a file
            output_path = kwargs.get("output_path", None)
            if not output_path:
                os.makedirs("temp", exist_ok=True)
                output_path = f"temp/runway_video_{int(time.time())}.mp4"
            
            with open(output_path, "wb") as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"Successfully saved RunwayML video to {output_path}")
                return {
                    "success": True,
                    "output_path": output_path,
                    "video_path": output_path,  # For backward compatibility
                    "video_url": video_url,
                    "duration": actual_duration
                }
            else:
                print(f"Failed to save video or file is empty: {output_path}")
                return {
                    "success": False,
                    "error": "Failed to save video or received empty response"
                }
                
        except Exception as e:
            error_message = f"RunwayML error: {str(e)}"
            print(error_message)
            import traceback
            print(traceback.format_exc())
            return {"success": False, "error": error_message}
    
    @staticmethod
    def generate_stable_video(prompt: str, duration: int = 3, **kwargs) -> Dict[str, Any]:
        """
        Generate a video using Stability AI's API
        
        Args:
            prompt (str): Text description of the video to generate
            duration (int): Duration in seconds (max 3 for SVD)
            
        Returns:
            dict: Result containing video path
        """
        if not STABILITY_API_KEY:
            print("ERROR: Stability AI key not configured")
            return {"success": False, "error": "Stability AI key not configured"}
        
        try:
            print(f"Starting Stability AI video generation with prompt: {prompt[:100]}...")
            
            # First, we need to generate an image from the prompt
            # Stability API endpoint for text-to-image generation
            url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
            
            # Request headers
            headers = {
                "Authorization": f"Bearer {STABILITY_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Request body for generating the initial image
            img_payload = {
                "text_prompts": [
                    {
                        "text": prompt,
                        "weight": 1.0
                    }
                ],
                "cfg_scale": kwargs.get("cfg_scale", 7),
                "height": 768,
                "width": 1344,
                "samples": 1,
                "steps": 30
            }
            
            print(f"Generating initial image with Stability AI: {url}")
            print(f"Image generation payload: {json.dumps(img_payload)}")
            
            # Make the request to generate an image
            img_response = requests.post(url, headers=headers, json=img_payload)
            
            if img_response.status_code != 200:
                error_detail = f"HTTP {img_response.status_code}: {img_response.text}"
                print(f"Stability API image generation error: {error_detail}")
                return {
                    "success": False, 
                    "error": f"Stability API image generation error: {error_detail}"
                }
            
            print("Stability API image generation successful!")
            
            # Save the generated image
            os.makedirs("temp", exist_ok=True)
            img_timestamp = int(time.time())
            img_path = f"temp/stability_img_{img_timestamp}.png"
            
            # Extract and decode the base64 image data
            img_data = img_response.json()["artifacts"][0]["base64"]
            with open(img_path, "wb") as f:
                f.write(base64.b64decode(img_data))
            
            if not os.path.exists(img_path):
                print(f"Failed to save generated image to {img_path}")
                return {
                    "success": False,
                    "error": "Failed to save generated image"
                }
            
            print(f"Successfully saved image to {img_path}. Now generating video from this image.")
            
            # Now use the image-to-video endpoint
            video_url = "https://api.stability.ai/v1/generation/stable-video-diffusion/image-to-video"
            
            # Prepare form data with the image
            with open(img_path, "rb") as img_file:
                files = {
                    "image": (os.path.basename(img_path), img_file, "image/png")
                }
                
                data = {
                    "seed": str(kwargs.get("seed", random.randint(1, 1000000))),
                    "cfg_scale": str(kwargs.get("cfg_scale", 2.5)),
                    "motion_bucket_id": str(kwargs.get("motion_bucket_id", 40)),
                    "fps": "24"
                }
                
                print(f"Sending image-to-video request to Stability AI: {video_url}")
                print(f"Video generation params: {data}")
                
                # Make the request
                video_response = requests.post(
                    video_url,
                    headers={"Authorization": f"Bearer {STABILITY_API_KEY}"},
                    files=files,
                    data=data
                )
            
            if video_response.status_code != 200:
                error_detail = f"HTTP {video_response.status_code}: {video_response.text}"
                print(f"Stability API video generation error: {error_detail}")
                return {
                    "success": False, 
                    "error": f"Stability API video generation error: {error_detail}"
                }
            
            print("Stability API video generation successful!")
            
            # Save the video
            video_timestamp = int(time.time())
            local_path = kwargs.get("output_path") or f"temp/svd_video_{video_timestamp}.mp4"
            
            with open(local_path, "wb") as f:
                f.write(video_response.content)
            
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                print(f"Successfully saved Stability AI video to {local_path}")
                return {
                    "success": True,
                    "output_path": local_path,
                    "video_path": local_path,
                    "duration": 3  # SVD generates fixed 3-second videos
                }
            else:
                print(f"Failed to save video or file is empty: {local_path}")
                return {
                    "success": False,
                    "error": "Failed to save video or received empty response"
                }
            
        except Exception as e:
            error_message = f"Stability AI error: {str(e)}"
            print(error_message)
            import traceback
            print(traceback.format_exc())
            return {"success": False, "error": error_message}
    
    @staticmethod
    def fetch_stock_video(query, limit=5, output_path=None):
        """Fetch stock videos from Pexels based on a search query."""
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            return {"success": False, "error": "Pexels API key is not configured"}
        
        # Use TextProcessor to clean and optimize the query
        original_query = query
        query = TextProcessor.sanitize_prompt(query)
        
        print(f"Original query: {original_query[:100]}...")
        print(f"Sanitized query: {query[:100]}...")
        
        # Handle empty or malformed queries
        if not query or not query.strip():
            query = "business presentation"
            print("Empty query provided, using default: 'business presentation'")
        
        # Get video type scores to better understand the intent
        video_type_scores = TextProcessor.detect_video_type(query)
        primary_video_type = max(video_type_scores.items(), key=lambda x: x[1])[0]
        
        print(f"Detected stock video type: {primary_video_type}")
        
        # Optimize query based on detected video type
        if primary_video_type == "testimonial":
            # For testimonial videos, focus on people talking
            optimized_query = "professional person talking interview testimonial"
            print(f"Optimized testimonial query: {optimized_query}")
        elif primary_video_type == "commercial":
            # For commercials, extract product/service terms
            key_entities = TextProcessor.extract_key_entities(query)
            product_terms = [term for term in key_entities if len(term) > 3]
            if product_terms:
                optimized_query = f"{' '.join(product_terms[:3])} advertisement professional"
            else:
                optimized_query = "professional business advertisement"
            print(f"Optimized commercial query: {optimized_query}")
        elif primary_video_type == "cinematic":
            # For cinematic content, focus on visual aesthetics
            optimized_query = f"cinematic scene {query.split()[-3] if len(query.split()) > 3 else query}"
            print(f"Optimized cinematic query: {optimized_query}")
        else:
            # Keep original query but ensure it's not too long
            words = query.split()
            optimized_query = " ".join(words[:6]) if len(words) > 6 else query
        
        # Use the optimized query
        query = optimized_query
        
        # URL encode the query
        encoded_query = urllib.parse.quote(query)
        
        print(f"Original query: '{query}'")
        print(f"Processed query: '{optimized_query}'")
        print(f"Encoded query: '{encoded_query}'")
        
        headers = {
            "Authorization": api_key
        }
        
        url = f"https://api.pexels.com/videos/search?query={encoded_query}&per_page={limit}"
        
        try:
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"Pexels API error: {response.text}")
                # Fall back to a generic query if the specific one fails
                fallback_url = f"https://api.pexels.com/videos/search?query=business&per_page={limit}"
                print("Trying fallback query: business")
                response = requests.get(fallback_url, headers=headers)
                
                if response.status_code != 200:
                    return {"success": False, "error": f"Pexels API error: {response.text}"}
            
            data = response.json()
            videos = data.get("videos", [])
            
            if not videos:
                # If no videos found, try another fallback
                fallback_terms = ["professional", "technology", "office"]
                for term in fallback_terms:
                    print(f"No videos found, trying fallback term: {term}")
                    fallback_url = f"https://api.pexels.com/videos/search?query={term}&per_page={limit}"
                    response = requests.get(fallback_url, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        videos = data.get("videos", [])
                        if videos:
                            break
            
            if not videos:
                return {"success": False, "error": "No suitable stock videos found"}
            
            # Continue with existing functionality to select a video
            selected_video = None
            for video in videos:
                # Find a video file that's not too large (under 10MB)
                for video_file in video.get("video_files", []):
                    if video_file.get("file_type") == "video/mp4" and video_file.get("width", 0) >= 1280:
                        file_size_mb = video_file.get("file_size", 0) / (1024 * 1024)
                        if file_size_mb < 10:  # Less than 10MB
                            selected_video = video_file
                            break
                if selected_video:
                    break
            
            if not selected_video:
                return {"success": False, "error": "No suitable video files found (under 10MB)"}
            
            # If output_path is provided, download the video to that path
            if output_path:
                try:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # Download the video
                    video_url = selected_video.get("link")
                    print(f"Downloading stock video from {video_url} to {output_path}")
                    response = requests.get(video_url, stream=True)
                    
                    if response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        return {
                            "success": True,
                            "video_path": output_path,
                            "duration": video.get("duration", 10)
                        }
                    else:
                        return {"success": False, "error": f"Failed to download video: HTTP {response.status_code}"}
                except Exception as e:
                    print(f"Error downloading stock video to output path: {str(e)}")
                    return {"success": False, "error": f"Error downloading video: {str(e)}"}
            
            # Return success with the video link if no output_path
            return {
                "success": True,
                "video_path": selected_video.get("link"),
                "duration": video.get("duration", 10)  # Duration in seconds
            }
            
        except Exception as e:
            print(f"Error fetching stock video: {str(e)}")
            return {"success": False, "error": f"Failed to fetch stock video: {str(e)}"}
    
    @staticmethod
    def get_best_video_service(prompt: str, duration: int) -> str:
        """
        Determine the best video service to use based on the prompt and duration
        
        Args:
            prompt (str): Text description for the video
            duration (int): Desired duration in seconds
            
        Returns:
            str: Name of the recommended service ('runway', 'stability', 'pexels')
        """
        # If the prompt contains specific keywords like "3D", "animation", use RunwayML
        animation_keywords = ["3d", "animation", "animated", "motion graphics", "cartoon"]
        if any(keyword in prompt.lower() for keyword in animation_keywords):
            return "runway"
        
        # For realistic scenes, use stock videos
        realistic_keywords = ["real", "realistic", "footage", "film", "actual", "documentary"]
        if any(keyword in prompt.lower() for keyword in realistic_keywords):
            return "pexels"
        
        # For longer videos (>4 seconds), use Pexels stock videos
        if duration > 4:
            return "pexels"
        
        # For creative, artistic content, use Stable Video Diffusion
        creative_keywords = ["artistic", "creative", "surreal", "dreamlike", "fantasy"]
        if any(keyword in prompt.lower() for keyword in creative_keywords):
            return "stability"
        
        # Default to RunwayML for general cases
        return "runway"
    
    @staticmethod
    def generate_video_from_text(prompt: str, style: str = "realistic", duration: float = 10.0, output_path: str = None, video_source: str = None) -> str:
        """
        Generate a video from text description using the best available service
        
        Args:
            prompt (str): Text description of the video to generate
            style (str): Style of the video (realistic, animated, etc.)
            duration (float): Duration in seconds
            output_path (str): Path to save the output video
            video_source (str): Preferred video source (runway, stability, pexels, hybrid)
            
        Returns:
            str: Path to the output video
        """
        # Clean the prompt using our TextProcessor
        original_prompt = prompt
        prompt = TextProcessor.sanitize_prompt(prompt)
        print(f"Original prompt: {original_prompt[:100]}...")
        print(f"Sanitized prompt: {prompt[:100]}...")
        
        # Detect video type
        video_type_scores = TextProcessor.detect_video_type(prompt)
        primary_video_type = max(video_type_scores.items(), key=lambda x: x[1])[0]
        
        print(f"Detected video type: {primary_video_type} with scores: {video_type_scores}")
        
        # Only auto-select video source if not explicitly provided
        if not video_source:
            suggested_params = TextProcessor.suggest_video_parameters(primary_video_type)
            video_source = suggested_params.get("preferred_source")
            
            # If style was not explicitly requested, use the suggested style
            if style == "realistic":  # Only override if using the default
                style = suggested_params.get("style", style)
                
            # Log the auto-selected parameters
            print(f"Auto-selected parameters based on content: source={video_source}, style={style}")
        else:
            print(f"Using explicitly requested video source: {video_source}")
            
        # Extract key entities for context retention
        key_entities = TextProcessor.extract_key_entities(prompt)
        if key_entities:
            print(f"Extracted key entities for context: {', '.join(key_entities)}")
            
        # Handle testimonial videos specially
        is_testimonial = video_type_scores.get("testimonial", 0) > 0.5
        
        # If this is a testimonial video, modify the prompt to get better results
        if is_testimonial:
            print(f"Detected testimonial video request: {prompt[:100]}...")
            # Add explicit instructions for face framing if not already present
            if "talking head" not in prompt.lower() and "speaking to camera" not in prompt.lower():
                prompt = f"Close-up shot of a person speaking directly to camera, showing face and upper body, making eye contact: {prompt}"
        
        # Always convert video_source to lowercase for comparisons
        video_source = video_source.lower() if video_source else ""
        
        # First, try the explicitly requested video source
        if video_source == "runway":
            print("Using RunwayML for video generation (explicitly requested)")
            if not RUNWAYML_API_KEY:
                print("ERROR: RunwayML API key is not configured")
                return {"success": False, "error": "RunwayML API key is not configured. Please set RUNWAYML_API_KEY in your .env file."}
                
            try:
                result = VideoGenerationService.generate_runway_video(prompt, min(int(duration), 4), output_path=output_path)
                if result.get("success", False) and os.path.exists(result.get("output_path", "")):
                    return result["output_path"]
                else:
                    error_msg = result.get("error", "Unknown error with RunwayML")
                    print(f"RunwayML generation failed: {error_msg}")
                    return {"success": False, "error": error_msg}
            except Exception as e:
                print(f"RunwayML exception: {str(e)}")
                return {"success": False, "error": f"RunwayML exception: {str(e)}"}
                
        elif video_source == "stability":
            print("Using StabilityAI for video generation (explicitly requested)")
            if not STABILITY_API_KEY:
                print("ERROR: Stability API key is not configured")
                return {"success": False, "error": "Stability API key is not configured. Please set STABILITY_API_KEY in your .env file."}
                
            try:
                result = VideoGenerationService.generate_stable_video(prompt, min(int(duration), 4), output_path=output_path)
                if result.get("success", False) and os.path.exists(result.get("output_path", "")):
                    return result["output_path"]
                else:
                    error_msg = result.get("error", "Unknown error with Stability AI")
                    print(f"Stability AI generation failed: {error_msg}")
                    return {"success": False, "error": error_msg}
            except Exception as e:
                print(f"Stability AI exception: {str(e)}")
                return {"success": False, "error": f"Stability AI exception: {str(e)}"}
                
        elif video_source == "pexels":
            print("Using Pexels for video (explicitly requested)")
            if not PEXELS_API_KEY:
                print("ERROR: Pexels API key is not configured")
                return {"success": False, "error": "Pexels API key is not configured. Please set PEXELS_API_KEY in your .env file."}
                
            try:
                result = VideoGenerationService.fetch_stock_video(query=prompt, limit=5, output_path=output_path)
                if result.get("success", False) and os.path.exists(result.get("video_path", "")):
                    return result["video_path"]
                else:
                    error_msg = result.get("error", "Unknown error with Pexels")
                    print(f"Pexels stock video failed: {error_msg}")
                    return {"success": False, "error": error_msg}
            except Exception as e:
                print(f"Pexels exception: {str(e)}")
                return {"success": False, "error": f"Pexels exception: {str(e)}"}
                
        elif video_source == "hybrid":
            print("Using hybrid approach for video generation (explicitly requested)")
            try:
                result = VideoGenerationService.generate_hybrid_video(prompt, duration, style, output_path=output_path, max_attempts=1)
                if isinstance(result, str) and os.path.exists(result):
                    return result
                elif isinstance(result, dict) and result.get("success", False) and os.path.exists(result.get("video_path", "")):
                    return result["video_path"]
                else:
                    error_msg = result.get("error", "Unknown error with hybrid generation")
                    print(f"Hybrid generation failed: {error_msg}")
                    return {"success": False, "error": error_msg}
            except Exception as e:
                print(f"Hybrid generation exception: {str(e)}")
                return {"success": False, "error": f"Hybrid generation exception: {str(e)}"}
        
        # If we get here with a video_source that wasn't recognized, or if no source was specified,
        # try all available methods in sequence
        print("No specific video source recognized or no source specified. Trying all available methods...")
        
        errors = []
        
        # Try RunwayML first
        if RUNWAYML_API_KEY:
            try:
                print("Attempting video generation with RunwayML...")
                result = VideoGenerationService.generate_runway_video(prompt, min(int(duration), 4), output_path=output_path)
                if result.get("success", False) and result.get("output_path") and os.path.exists(result.get("output_path")):
                    return result["output_path"]
                else:
                    errors.append(f"RunwayML: {result.get('error', 'Unknown error')}")
            except Exception as e:
                errors.append(f"RunwayML exception: {str(e)}")
        
        # Then try Stability
        if STABILITY_API_KEY:
            try:
                print("Attempting video generation with Stability AI...")
                result = VideoGenerationService.generate_stable_video(prompt, min(int(duration), 4), output_path=output_path)
                if result.get("success", False) and result.get("output_path") and os.path.exists(result.get("output_path")):
                    return result["output_path"]
                else:
                    errors.append(f"Stability: {result.get('error', 'Unknown error')}")
            except Exception as e:
                errors.append(f"Stability exception: {str(e)}")
        
        # Try Pexels stock video as a fallback
        if PEXELS_API_KEY:
            try:
                print("Fetching stock video from Pexels as fallback...")
                result = VideoGenerationService.fetch_stock_video(query=prompt, limit=5, output_path=output_path)
                if result.get("success", False) and result.get("video_path") and os.path.exists(result.get("video_path")):
                    return result["video_path"]
                else:
                    errors.append(f"Pexels: {result.get('error', 'Unknown error')}")
            except Exception as e:
                errors.append(f"Pexels exception: {str(e)}")
        
        # Last resort: Try the hybrid approach
        try:
            print("Attempting hybrid video generation as last resort...")
            result = VideoGenerationService.generate_hybrid_video(prompt, duration, style, output_path=output_path, max_attempts=1)
            if isinstance(result, str) and os.path.exists(result):
                return result
            elif isinstance(result, dict) and result.get("success", False) and os.path.exists(result.get("video_path", "")):
                return result["video_path"]
            else:
                errors.append(f"Hybrid: {result.get('error', 'Unknown error')}")
        except Exception as e:
            errors.append(f"Hybrid exception: {str(e)}")
        
        # If all methods fail, return a detailed error
        error_message = "Failed to generate video with any available method. Errors: " + "; ".join(errors)
        print(error_message)
        return {"success": False, "error": error_message}
    
    @staticmethod
    def generate_hybrid_video(prompt, duration=10, style="creative", output_path=None, max_attempts=1):
        """
        Generate a hybrid video using a combination of AI-generated and stock footage.
        
        Args:
            prompt (str): Text description of what to generate
            duration (float): Target duration in seconds (should be float)
            style (str): Style preference ("realistic", "animated", "creative")
            output_path (str, optional): Path to save the output video
            max_attempts (int): Maximum number of attempts per segment to prevent infinite loops
            
        Returns:
            str or dict: If successful, returns the file path as a string. 
                        If unsuccessful, returns a dictionary with error information.
        """
        from moviepy.editor import VideoFileClip, concatenate_videoclips
        import tempfile
        
        # Sanitize the prompt
        original_prompt = prompt
        prompt = TextProcessor.sanitize_prompt(prompt)
        print(f"Hybrid generation with sanitized prompt: {prompt[:100]}...")
        
        # Ensure duration is a number
        try:
            duration = float(duration) if duration else 10.0
        except (ValueError, TypeError):
            print(f"Warning: Invalid duration value '{duration}', using default 10.0")
            duration = 10.0
            
        print(f"Hybrid generation with duration: {duration}, type: {type(duration)}")
        
        # Detect video type for optimal segment generation
        video_type_scores = TextProcessor.detect_video_type(prompt)
        primary_video_type = max(video_type_scores.items(), key=lambda x: x[1])[0]
        print(f"Detected hybrid video type: {primary_video_type}")
        
        # Extract key entities for context
        key_entities = TextProcessor.extract_key_entities(prompt)
        entity_context = ", ".join(key_entities[:3]) if key_entities else ""
        
        # Create a temporary directory to store our video segments
        with tempfile.TemporaryDirectory() as temp_dir:
            segments = []
            segment_prompts = []
            
            # Check for testimonial video
            is_testimonial = any(keyword in prompt.lower() for keyword in ["testimonial", "talking head", "interview"])
            
            # Based on the prompt, create segments for different parts
            # For testimonial videos, handle them specially
            if is_testimonial:
                print("Creating specialized testimonial hybrid video")
                
                # Extract key elements from the prompt
                import re
                # Look for industry terms
                industry_terms = {
                    "hvac": ["hvac", "air conditioning", "heating", "cooling", "technician"],
                    "construction": ["construction", "builder", "contractor"],
                    "real estate": ["real estate", "property", "realtor", "agent"],
                    "other": ["business", "professional", "service"]
                }
                
                # Find the specific industry mentioned
                detected_industry = "business"  # Default
                for industry, terms in industry_terms.items():
                    if any(term in prompt.lower() for term in terms):
                        detected_industry = industry
                        break
                
                # Try to extract specific scenes from the prompt
                scenes = []
                scene_matches = re.finditer(r'Scene\s*\d+\s*:\s*([^.]+)', prompt)
                for match in scene_matches:
                    scenes.append(match.group(1).strip())
                
                if not scenes:  # If no explicit scenes found, create segments based on common settings
                    # Default testimonial structure
                    scenes = [
                        f"{detected_industry} professional talking to camera in office setting",
                        f"{detected_industry} worker at job site",
                        f"{detected_industry} team working together"
                    ]
                
                # Create segments based on scenes, trying to maintain continuity with the same person
                first_scene_prompt = scenes[0]
                if "hvac" in detected_industry:
                    first_scene_prompt = f"HVAC technician in work clothes talking to camera: {first_scene_prompt}"
                elif "construction" in detected_industry:
                    first_scene_prompt = f"Construction worker with hard hat talking to camera: {first_scene_prompt}"
                
                # Main talking head segment - this is critical for lip sync
                segment_prompts.append({
                    "prompt": first_scene_prompt,
                    "source": "pexels",
                    "duration": min(duration * 0.7, 20)  # Use most of the duration for the main segment
                })
                
                # Add B-roll if we have multiple scenes and enough duration
                if len(scenes) > 1 and duration > 10:
                    for i, scene in enumerate(scenes[1:]):
                        if i >= 2:  # Limit to max 3 total segments
                            break
                        segment_prompts.append({
                            "prompt": scene,
                            "source": "pexels",
                            "duration": min(5.0, duration * 0.15)  # Shorter B-roll segments
                        })
            else:
                # Standard multi-segment approach for non-testimonials
                if "intro" in prompt.lower() or "opening" in prompt.lower():
                    # Split the prompt to find intro/opening part
                    prompt_parts = prompt.split(".")
                    intro_prompt = next((part for part in prompt_parts if "intro" in part.lower() or "opening" in part.lower()), prompt_parts[0])
                    segment_prompts.append({"prompt": intro_prompt, "source": "pexels", "duration": 3.0})
                
                # Find a middle section
                middle_prompt = prompt
                # Calculate middle duration as a float
                middle_duration = max(4.0, float(duration) - 6.0)
                segment_prompts.append({"prompt": middle_prompt, "source": "pexels", "duration": middle_duration})
                
                # Add a closing section if mentioned
                if "conclusion" in prompt.lower() or "ending" in prompt.lower() or "closing" in prompt.lower():
                    prompt_parts = prompt.split(".")
                    closing_prompt = next((part for part in prompt_parts if any(word in part.lower() for word in ["conclusion", "ending", "closing"])), prompt_parts[-1])
                    segment_prompts.append({"prompt": closing_prompt, "source": "pexels", "duration": 3.0})
                
                # If we don't have at least 2 segments, add a default ending
                if len(segment_prompts) < 2:
                    segment_prompts.append({"prompt": "closing shot, " + prompt, "source": "pexels", "duration": 3.0})
            
            print(f"Creating hybrid video with {len(segment_prompts)} segments")
            for i, segment in enumerate(segment_prompts):
                print(f"Segment {i+1}: {segment['prompt'][:50]}... (duration: {segment['duration']}s)")
            
            # Generate each segment - only use direct methods, not hybrid
            for i, segment in enumerate(segment_prompts):
                segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
                
                # Generate this segment using the specified source, never using hybrid
                try:
                    segment_duration = float(segment["duration"])
                    
                    # Make sure we don't use hybrid for segments to avoid recursion
                    segment_source = "pexels"  # Default to Pexels for all segments to prevent recursion
                    
                    # Limit to a single attempt to prevent multiple downloads
                    print(f"Generating segment {i} with source '{segment_source}'")
                    
                    result = VideoGenerationService.generate_video_from_text(
                        prompt=segment["prompt"],
                        style=style,
                        duration=segment_duration,
                        output_path=segment_path,
                        video_source=segment_source  # Force stable source to prevent recursion
                    )
                    
                    # If successful, add to segments
                    if isinstance(result, str) and os.path.exists(result):
                        segments.append(result)
                        print(f"Successfully generated segment {i}")
                    elif isinstance(result, dict) and result.get("success", False) and os.path.exists(result.get("video_path", "")):
                        segments.append(result.get("video_path"))
                        print(f"Successfully generated segment {i}")
                    else:
                        print(f"Failed to generate segment {i}")
                    
                except Exception as e:
                    print(f"Error generating segment {i}: {str(e)}")
                    # Continue with other segments
            
            # If we don't have any successful segments, return error
            if not segments:
                return {"success": False, "error": "Failed to generate any video segments"}
            
            try:
                # Combine all segments into one video
                video_clips = [VideoFileClip(segment) for segment in segments]
                final_clip = concatenate_videoclips(video_clips)
                
                # Write to output path
                if output_path:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    final_path = output_path
                else:
                    # Create a default output path
                    os.makedirs("output", exist_ok=True)
                    final_path = f"output/hybrid_video_{int(time.time())}.mp4"
                
                final_clip.write_videofile(
                    final_path,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=os.path.join(temp_dir, "temp_audio.m4a"),
                    remove_temp=True,
                    fps=24
                )
                
                return final_path
                
            except Exception as e:
                error_message = f"Error combining video segments: {str(e)}"
                print(error_message)
                return {"success": False, "error": error_message} 