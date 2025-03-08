import os
from typing import List, Dict, Any
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips, AudioFileClip
from moviepy.video.fx import all as vfx
import tempfile
from dotenv import load_dotenv

load_dotenv()

class VideoProcessor:
    def __init__(self):
        self.output_dir = os.getenv("OUTPUT_DIR", "./output")
        self.temp_dir = os.getenv("TEMP_DIR", "./temp")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    def apply_effect(self, clip, effect_name: str) -> VideoFileClip:
        """Apply a specific effect to a video clip."""
        effects = {
            "zoom": lambda c: c.fx(vfx.zoom, 1.5),
            "fade_in": lambda c: c.fadein(1),
            "fade_out": lambda c: c.fadeout(1),
            "mirror": lambda c: c.fx(vfx.mirror_x),
            "color_enhance": lambda c: c.fx(vfx.colorx, 1.2),
            "slow_motion": lambda c: c.fx(vfx.speedx, 0.5),
            "fast_motion": lambda c: c.fx(vfx.speedx, 1.5),
        }
        
        if effect_name in effects:
            return effects[effect_name](clip)
        return clip

    def create_video_from_image(
        self,
        image_path: str,
        duration: int,
        effects: List[str],
        style: str,
        background_music: str = None
    ) -> Dict[str, Any]:
        """Create a video from a single image with effects."""
        try:
            # Create base clip from image
            base_clip = ImageClip(image_path).set_duration(duration)
            
            # Apply effects in sequence
            final_clip = base_clip
            for effect in effects:
                final_clip = self.apply_effect(final_clip, effect)
            
            # Add background music if provided
            if background_music and os.path.exists(background_music):
                audio = AudioFileClip(background_music)
                if audio.duration < duration:
                    audio = audio.loop(duration=duration)
                final_clip = final_clip.set_audio(audio)
            
            # Generate output filename
            output_filename = f"video_{os.path.basename(image_path)}_{int(duration)}s.mp4"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Write final video
            final_clip.write_videofile(
                output_path,
                fps=int(os.getenv("VIDEO_FPS", "30")),
                bitrate=os.getenv("VIDEO_BITRATE", "4000k"),
                codec='libx264',
                audio_codec='aac'
            )
            
            # Clean up
            final_clip.close()
            if background_music:
                audio.close()
            
            return {
                "success": True,
                "output_path": output_path,
                "filename": output_filename
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def create_transition(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float = 1.0) -> VideoFileClip:
        """Create a smooth transition between two clips."""
        try:
            # Fade out first clip
            clip1 = clip1.fadeout(duration)
            
            # Fade in second clip
            clip2 = clip2.fadein(duration)
            
            # Concatenate clips
            return concatenate_videoclips([clip1, clip2])
        except Exception as e:
            raise Exception(f"Failed to create transition: {str(e)}")

    def add_text_overlay(
        self,
        clip: VideoFileClip,
        text: str,
        position: tuple = ('center', 'center'),
        fontsize: int = 70,
        color: str = 'white',
        duration: float = None
    ) -> VideoFileClip:
        """Add text overlay to a video clip."""
        try:
            from moviepy.editor import TextClip
            
            text_clip = TextClip(
                text,
                fontsize=fontsize,
                color=color,
                size=(clip.w, None),
                method='caption'
            )
            
            if duration:
                text_clip = text_clip.set_duration(duration)
            else:
                text_clip = text_clip.set_duration(clip.duration)
            
            text_clip = text_clip.set_position(position)
            
            return clip.set_mask(text_clip)
        except Exception as e:
            raise Exception(f"Failed to add text overlay: {str(e)}") 