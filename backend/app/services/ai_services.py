import os
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()

class AIServices:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4-vision-preview")

    async def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Analyze an image using OpenAI's vision model."""
        try:
            with open(image_path, "rb") as image_file:
                response = self.client.chat.completions.create(
                    model=self.model,
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
                                        "url": f"data:image/jpeg;base64,{image_file.read()}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=500
                )
                return {"analysis": response.choices[0].message.content}
        except Exception as e:
            return {"error": str(e)}

    async def generate_video_script(self, image_analysis: str, style: str, duration: int) -> Dict[str, Any]:
        """Generate a video script based on image analysis and style preferences."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
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
            return {"error": str(e)}

    async def suggest_effects(self, image_analysis: str, style: str) -> List[str]:
        """Suggest video effects based on image analysis and style."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a video effects specialist."
                    },
                    {
                        "role": "user",
                        "content": f"""
                        Suggest 5-7 video effects that would work well for this content:
                        - Style: {style}
                        - Person Analysis: {image_analysis}
                        
                        Return only a JSON array of effect names.
                        """
                    }
                ],
                max_tokens=200
            )
            effects = json.loads(response.choices[0].message.content)
            return effects
        except Exception as e:
            return ["error", str(e)] 