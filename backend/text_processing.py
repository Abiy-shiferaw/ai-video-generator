import re
import string
from typing import Dict, List, Optional, Tuple

class TextProcessor:
    """
    A utility class for preprocessing and sanitizing text prompts for video generation
    """
    
    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """
        Clean and sanitize prompt text by removing markdown elements, 
        special characters, and normalizing whitespace
        
        Args:
            prompt (str): Raw input prompt
            
        Returns:
            str: Cleaned prompt ready for video generation
        """
        if not prompt:
            return ""
        
        # Remove markdown bold symbols
        prompt = re.sub(r'\*\*(.*?)\*\*', r'\1', prompt)
        
        # Remove markdown headers
        prompt = re.sub(r'^#{1,6}\s+', '', prompt, flags=re.MULTILINE)
        
        # Remove markdown lists
        prompt = re.sub(r'^\s*[-*+]\s+', '', prompt, flags=re.MULTILINE)
        
        # Remove excessive whitespace
        prompt = re.sub(r'\s+', ' ', prompt)
        
        # Remove other special characters that might confuse the AI
        prompt = re.sub(r'[^\w\s.,!?:;()\-\'"]+', ' ', prompt)
        
        return prompt.strip()
    
    @staticmethod
    def detect_video_type(prompt: str) -> Dict[str, float]:
        """
        Analyze the text prompt to detect the most likely video type
        
        Args:
            prompt (str): The preprocessed text prompt
            
        Returns:
            Dict[str, float]: Dictionary with video types and confidence scores (0-1)
        """
        prompt = prompt.lower()
        
        # Define keywords for each video type
        keywords = {
            "commercial": [
                "advertisement", "ad ", "commercial", "product", "brand", "promotional", 
                "marketing", "showcase", "sell", "promote", "business", "service"
            ],
            "testimonial": [
                "testimonial", "talking head", "interview", "speaking", "person talking", 
                "face to camera", "spokesperson", "presenter", "monologue", "speaking directly"
            ],
            "cinematic": [
                "cinematic", "film", "movie", "scene", "dramatic", "storytelling", "narrative", 
                "aesthetic", "artistic", "atmosphere", "mood", "visual story", "epic"
            ],
            "stock": [
                "stock footage", "b-roll", "background video", "generic", "simple", 
                "everyday", "natural", "real life", "documentary style"
            ]
        }
        
        # Calculate scores for each type
        scores = {}
        for video_type, type_keywords in keywords.items():
            score = sum(1 for keyword in type_keywords if keyword in prompt)
            # Normalize score (0-1)
            scores[video_type] = min(score / 4, 1.0)
            
        # Boost testimonial score if it contains direct references
        if any(kw in prompt for kw in ["face", "person", "people", "talking", "speaking"]):
            scores["testimonial"] = min(scores.get("testimonial", 0) + 0.3, 1.0)
        
        # Boost commercial score if it mentions specific products/services
        if any(kw in prompt for kw in ["product", "service", "buy", "purchase", "sale"]):
            scores["commercial"] = min(scores.get("commercial", 0) + 0.3, 1.0)
            
        # Ensure all types have a score
        for video_type in keywords.keys():
            if video_type not in scores:
                scores[video_type] = 0.0
                
        return scores
    
    @staticmethod
    def suggest_video_parameters(video_type: str) -> Dict[str, any]:
        """
        Suggest optimal video parameters based on detected video type
        
        Args:
            video_type (str): Detected video type
            
        Returns:
            Dict[str, any]: Dictionary with suggested parameters
        """
        params = {
            "commercial": {
                "duration": 15.0,
                "preferred_source": "hybrid",
                "style": "polished",
                "aspect_ratio": "16:9",
                "camera_movement": "dynamic"
            },
            "testimonial": {
                "duration": 20.0,
                "preferred_source": "runway",  # RunwayML handles faces well
                "style": "realistic",
                "aspect_ratio": "9:16",  # Vertical for social media
                "camera_movement": "static"
            },
            "cinematic": {
                "duration": 10.0,
                "preferred_source": "stability",  # Stability AI has good aesthetic quality
                "style": "cinematic",
                "aspect_ratio": "21:9",  # Widescreen cinematic
                "camera_movement": "smooth"
            },
            "stock": {
                "duration": 8.0,
                "preferred_source": "pexels",
                "style": "natural",
                "aspect_ratio": "16:9",
                "camera_movement": "mixed"
            }
        }
        
        return params.get(video_type, {
            "duration": 10.0,
            "preferred_source": "hybrid",
            "style": "balanced",
            "aspect_ratio": "16:9",
            "camera_movement": "mixed"
        })
    
    @staticmethod
    def extract_key_entities(prompt: str) -> List[str]:
        """
        Extract key entities (people, objects, actions) from the prompt
        for better context tracking in multi-scene videos
        
        Args:
            prompt (str): The text prompt
            
        Returns:
            List[str]: List of extracted key entities
        """
        # Simple entity extraction (can be improved with NLP libraries)
        entities = []
        
        # Look for nouns after articles
        noun_patterns = [
            r'(?:the|a|an) ([a-z]+ing?)',
            r'(?:the|a|an) ([a-z]+)',
            r'([a-z]+ing) (?:the|a|an|in|on)',
            r'([a-z]+ [a-z]+) (?:is|are|was|were)'
        ]
        
        for pattern in noun_patterns:
            matches = re.findall(pattern, prompt.lower())
            entities.extend(matches)
            
        # Remove duplicates and common words
        common_words = ["the", "and", "or", "but", "with", "this", "that", "these", "those"]
        entities = [e for e in entities if len(e) > 3 and e not in common_words]
        
        return list(set(entities)) 