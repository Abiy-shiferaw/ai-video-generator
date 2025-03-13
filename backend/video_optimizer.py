import os
import tempfile
from typing import Dict, List, Optional, Any, Tuple

from text_processing import TextProcessor

class VideoOptimizer:
    """
    A service for optimizing video generation settings and post-processing
    based on detected content type and requirements
    """
    
    @staticmethod
    def get_optimal_generation_settings(prompt: str, user_preferences: Dict = None) -> Dict[str, Any]:
        """
        Determine the optimal video generation settings based on prompt analysis
        and user preferences
        
        Args:
            prompt (str): The sanitized text prompt
            user_preferences (Dict): Optional user preferences to consider
            
        Returns:
            Dict[str, Any]: Optimized settings for video generation
        """
        user_preferences = user_preferences or {}
        
        # Analyze the prompt to detect video type
        video_type_scores = TextProcessor.detect_video_type(prompt)
        primary_video_type = max(video_type_scores.items(), key=lambda x: x[1])[0]
        
        # Get baseline parameters for the detected type
        settings = TextProcessor.suggest_video_parameters(primary_video_type)
        
        # Adjust with any user preferences
        for key, value in user_preferences.items():
            if value is not None:  # Only override if explicitly provided
                settings[key] = value
                
        # Additional optimization based on content
        if primary_video_type == "testimonial":
            # For testimonial videos, add specific settings
            settings["frame_rate"] = 24  # Smoother motion
            settings["denoise"] = True   # Cleaner face rendering
            settings["face_enhancement"] = True
            
        elif primary_video_type == "commercial":
            # For commercial videos, optimize for engagement
            settings["frame_rate"] = 30  # Crisper motion
            settings["saturation_boost"] = 0.1  # Slightly boosted colors
            settings["clarity_boost"] = 0.15    # Added sharpness
            
        elif primary_video_type == "cinematic":
            # For cinematic videos, emulate film qualities
            settings["frame_rate"] = 24  # Film-like frame rate
            settings["cinematic_crop"] = True
            settings["color_grading"] = "film"
            
        return settings
    
    @staticmethod
    def should_use_hybrid_approach(prompt: str, duration: float) -> bool:
        """
        Determine if a hybrid approach (combining AI and stock footage) would be optimal
        
        Args:
            prompt (str): The sanitized text prompt
            duration (float): Requested video duration in seconds
            
        Returns:
            bool: True if hybrid approach is recommended
        """
        # Longer videos benefit from hybrid approach
        if duration > 15.0:
            return True
            
        # Complex prompts with multiple scenes/actions
        scene_indicators = ["scene", "then", "after that", "next", "followed by"]
        if any(indicator in prompt.lower() for indicator in scene_indicators):
            return True
            
        # Check for storytelling cues
        storytelling_cues = ["story", "narrative", "journey", "transformation", "process"]
        if any(cue in prompt.lower() for cue in storytelling_cues):
            return True
            
        # Default to False for simple, short videos
        return False
    
    @staticmethod
    def detect_scene_transitions(prompt: str) -> List[Dict[str, Any]]:
        """
        Detect natural scene transitions in the prompt
        
        Args:
            prompt (str): The sanitized text prompt
            
        Returns:
            List[Dict[str, Any]]: List of scene objects with start/end times
        """
        scenes = []
        
        # Check for explicit scene markers
        import re
        explicit_scenes = re.findall(r'scene\s*\d+:?\s*([^.;!?]*[.;!?])', prompt.lower())
        
        if explicit_scenes:
            # Calculate approximate duration for each scene
            scene_count = len(explicit_scenes)
            for i, scene_text in enumerate(explicit_scenes):
                scenes.append({
                    "index": i,
                    "description": scene_text.strip(),
                    "relative_duration": 1.0 / scene_count
                })
        else:
            # Look for natural transitions in text
            sentences = re.split(r'[.!?;]', prompt)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) > 1:
                for i, sentence in enumerate(sentences):
                    scenes.append({
                        "index": i,
                        "description": sentence,
                        "relative_duration": 1.0 / len(sentences)
                    })
            else:
                # Single scene
                scenes.append({
                    "index": 0, 
                    "description": prompt,
                    "relative_duration": 1.0
                })
                
        return scenes
    
    @staticmethod
    def optimize_motion_smoothness(video_path: str, settings: Dict[str, Any]) -> str:
        """
        Apply motion smoothing and optimization to the generated video
        
        Args:
            video_path (str): Path to the input video
            settings (Dict[str, Any]): Optimization settings
            
        Returns:
            str: Path to the optimized video
        """
        # This would integrate with external libraries like RIFE for frame interpolation
        # or other video processing techniques
        
        # Placeholder for actual implementation
        print(f"Would apply motion smoothing with settings: {settings}")
        
        # For now, just return the original path
        return video_path 
        
    def recommend_duration(self, prompt: str, user_requested_duration: int) -> int:
        """
        Recommend an optimal duration for the video based on content analysis
        
        Args:
            prompt (str): The text prompt describing the video
            user_requested_duration (int): User requested duration in seconds
            
        Returns:
            int: Recommended duration in seconds
        """
        # Default to user's requested duration
        recommended_duration = user_requested_duration
        
        # Simple logic: longer text likely needs more time
        word_count = len(prompt.split())
        
        # Very short prompts (<10 words) might be fine with shorter videos
        if word_count < 10 and user_requested_duration > 10:
            recommended_duration = 10
            
        # Longer prompts (>50 words) might need more time
        elif word_count > 50 and user_requested_duration < 20:
            recommended_duration = max(20, user_requested_duration)
            
        # Very long prompts (>100 words) almost certainly need more time
        elif word_count > 100 and user_requested_duration < 30:
            recommended_duration = max(30, user_requested_duration)
            
        # Cap at 60 seconds for very long content to keep processing time reasonable
        recommended_duration = min(recommended_duration, 60)
        
        return recommended_duration
        
    def recommend_style(self, prompt: str, user_requested_style: str) -> str:
        """
        Recommend an optimal style for the video based on content analysis
        
        Args:
            prompt (str): The text prompt describing the video
            user_requested_style (str): User requested style
            
        Returns:
            str: Recommended style
        """
        # Default to user's requested style
        if user_requested_style:
            return user_requested_style
            
        prompt_lower = prompt.lower()
        
        # Check for style hints in the prompt
        if any(word in prompt_lower for word in ["professional", "corporate", "business", "formal"]):
            return "professional"
            
        if any(word in prompt_lower for word in ["fun", "playful", "energetic", "vibrant"]):
            return "energetic"
            
        if any(word in prompt_lower for word in ["calm", "peaceful", "serene", "relaxing"]):
            return "calm"
            
        if any(word in prompt_lower for word in ["cinematic", "film", "movie", "dramatic"]):
            return "cinematic"
            
        # Default style
        return "standard" 