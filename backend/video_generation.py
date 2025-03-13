import os
import random
import tempfile
from typing import List, Dict, Any
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip, 
    CompositeVideoClip, concatenate_videoclips,
    TextClip, ColorClip
)
from moviepy.video.fx import all as vfx

# Explicitly import or define slide_in if not available
try:
    from moviepy.video.fx.all import slide_in
except ImportError:
    # Define a fallback slide_in function if not found in moviepy
    def slide_in(clip, duration=1.0, side="left"):
        """
        Custom implementation of slide_in effect for MoviePy.
        
        Args:
            clip: The video clip to apply the effect to
            duration: Duration of the slide effect in seconds
            side: Direction of the slide ("left", "right", "top", "bottom")
        
        Returns:
            A new clip with the slide effect applied
        """
        from moviepy.video.VideoClip import VideoClip
        import numpy as np
        
        def make_frame(t):
            # Get the original frame
            original_frame = clip.get_frame(t)
            h, w = original_frame.shape[:2]
            
            if t >= duration:
                return original_frame
            
            progress = t / duration  # 0 to 1
            
            # Create a black frame
            result = np.zeros_like(original_frame)
            
            if side == "left":
                offset = int((1 - progress) * w)
                result[:, :w-offset] = original_frame[:, offset:]
            elif side == "right":
                offset = int((1 - progress) * w)
                result[:, offset:] = original_frame[:, :w-offset]
            elif side == "top":
                offset = int((1 - progress) * h)
                result[:h-offset, :] = original_frame[offset:, :]
            elif side == "bottom":
                offset = int((1 - progress) * h)
                result[offset:, :] = original_frame[:h-offset, :]
            
            return result
        
        return VideoClip(make_frame, duration=clip.duration)
    
    # Register the custom effect if it wasn't available
    vfx.slide_in = slide_in
    print("Custom slide_in effect defined and registered.")

# Rest of the imports
# // ... existing code ... 