import os
import tempfile
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from moviepy.editor import (
    VideoFileClip, ImageClip, AudioFileClip, 
    CompositeVideoClip, concatenate_videoclips,
    TextClip, ColorClip, clips_array
)
from moviepy.video.fx import all as vfx
from moviepy.video.VideoClip import VideoClip

# Register custom effects at module import time
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

# Register the custom effects
vfx.slide_in = slide_in
print("Custom video effects registered successfully!")

class AdvancedVideoEffects:
    """
    Class for advanced video effects and animations using MoviePy
    """
    
    @staticmethod
    def create_zoom_effect(clip, zoom_ratio=0.3, duration_ratio=0.3):
        """
        Create a smooth zoom-in effect
        
        Args:
            clip: VideoClip or ImageClip to apply the effect to
            zoom_ratio: How much to zoom in (0.3 = 30%)
            duration_ratio: Duration of the zoom effect relative to clip length
            
        Returns:
            VideoClip with zoom effect applied
        """
        clip_duration = clip.duration
        zoom_duration = clip_duration * duration_ratio
        
        # Apply zoom effect
        def zoom(t):
            # Calculate the zoom factor at time t
            if t < zoom_duration:
                # Gradually zoom in during the first part
                zoom_factor = 1 + (zoom_ratio * t / zoom_duration)
            else:
                # Stay at maximum zoom for the rest
                zoom_factor = 1 + zoom_ratio
                
            return zoom_factor
            
        return clip.fx(vfx.resize, lambda t: zoom(t))
    
    @staticmethod
    def create_ken_burns_effect(clip, direction="left_to_right"):
        """
        Create a Ken Burns style pan and zoom effect
        
        Args:
            clip: VideoClip or ImageClip to apply the effect to
            direction: Direction of the pan effect 
                       ("left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top")
            
        Returns:
            VideoClip with Ken Burns effect applied
        """
        w, h = clip.size
        duration = clip.duration
        
        # Define the pan movement based on direction
        if direction == "left_to_right":
            # Start with the left side centered, end with the right side centered
            position_function = lambda t: ('center', 'center')
            cropbox_function = lambda t: (w*(0.6-0.2*t/duration), h*(0.8-0.0*t/duration))
            
        elif direction == "right_to_left":
            # Start with the right side centered, end with the left side centered
            position_function = lambda t: ('center', 'center')
            cropbox_function = lambda t: (w*(0.6-0.2*(1-t/duration)), h*(0.8-0.0*t/duration))
            
        elif direction == "top_to_bottom":
            # Start with the top centered, end with the bottom centered
            position_function = lambda t: ('center', 'center')
            cropbox_function = lambda t: (w*(0.8-0.0*t/duration), h*(0.6-0.2*t/duration))
            
        elif direction == "bottom_to_top":
            # Start with the bottom centered, end with the top centered
            position_function = lambda t: ('center', 'center')
            cropbox_function = lambda t: (w*(0.8-0.0*t/duration), h*(0.6-0.2*(1-t/duration)))
            
        else:
            # Default: zoom in at the center
            position_function = lambda t: ('center', 'center')
            cropbox_function = lambda t: (w*(1-0.3*t/duration), h*(1-0.3*t/duration))
        
        # Apply the pan and zoom
        return (clip
                .fx(vfx.crop, 
                    x_center=lambda t: position_function(t)[0],
                    y_center=lambda t: position_function(t)[1],
                    width=lambda t: cropbox_function(t)[0],
                    height=lambda t: cropbox_function(t)[1])
                .fx(vfx.resize, width=w, height=h))
    
    @staticmethod
    def create_3d_rotation_effect(clip, rotation_speed=0.5):
        """
        Create a 3D rotation effect (simulated)
        
        Args:
            clip: VideoClip or ImageClip to apply the effect to
            rotation_speed: Speed of rotation
            
        Returns:
            VideoClip with 3D rotation effect
        """
        duration = clip.duration
        
        # Apply a perspective-like transformation to simulate 3D rotation
        def transform_function(t):
            angle = rotation_speed * t * 2 * np.pi
            center = (clip.w/2, clip.h/2)
            
            # Calculate the corner points
            tl = (0, 0)
            tr = (clip.w, 0)
            br = (clip.w, clip.h)
            bl = (0, clip.h)
            
            # Apply a perspective transform
            offset_x = np.sin(angle) * clip.w * 0.1
            scale_y = 1 - np.abs(np.sin(angle) * 0.2)
            
            # Define the transformed corners
            new_tl = (tl[0] - offset_x, tl[1])
            new_tr = (tr[0] + offset_x, tr[1])
            new_br = (br[0] + offset_x, br[1] * scale_y)
            new_bl = (bl[0] - offset_x, bl[1] * scale_y)
            
            return [new_tl, new_tr, new_br, new_bl]
        
        return clip.fx(vfx.crop, x_center='center', y_center='center', width=clip.w*0.8, height=clip.h*0.8).fx(vfx.resize, width=clip.w, height=clip.h)
    
    @staticmethod
    def create_split_screen_effect(clips, layout=(2, 2)):
        """
        Create a split screen effect with multiple clips
        
        Args:
            clips: List of VideoClips to arrange in a grid
            layout: Tuple (rows, cols) defining the grid layout
            
        Returns:
            CompositeVideoClip with split screen effect
        """
        rows, cols = layout
        clips_matrix = []
        
        # Ensure we have enough clips to fill the grid
        while len(clips) < rows * cols:
            clips.append(clips[-1])  # Duplicate the last clip to fill the grid
        
        # Arrange clips in a grid
        for i in range(rows):
            row_clips = []
            for j in range(cols):
                idx = i * cols + j
                if idx < len(clips):
                    row_clips.append(clips[idx])
            
            if row_clips:
                clips_matrix.append(row_clips)
        
        return clips_array(clips_matrix)
    
    @staticmethod
    def create_picture_in_picture_effect(main_clip, pip_clip, position="bottom_right", size_ratio=0.3):
        """
        Create a picture-in-picture effect
        
        Args:
            main_clip: Main video clip
            pip_clip: Picture-in-picture video clip to overlay
            position: Position of the PiP ("bottom_right", "bottom_left", "top_right", "top_left")
            size_ratio: Size of the PiP relative to the main clip
            
        Returns:
            CompositeVideoClip with picture-in-picture effect
        """
        # Resize the PiP clip
        w, h = main_clip.size
        pip_w = int(w * size_ratio)
        pip_h = int(h * size_ratio)
        pip_clip = pip_clip.resize(width=pip_w)
        
        # Set PiP position
        padding = int(w * 0.03)  # 3% padding
        
        if position == "bottom_right":
            pos = (w - pip_w - padding, h - pip_clip.h - padding)
        elif position == "bottom_left":
            pos = (padding, h - pip_clip.h - padding)
        elif position == "top_right":
            pos = (w - pip_w - padding, padding)
        elif position == "top_left":
            pos = (padding, padding)
        else:
            pos = (w - pip_w - padding, h - pip_clip.h - padding)  # Default: bottom right
        
        # Add a border to the PiP
        pip_clip = pip_clip.margin(3, color=(255, 255, 255))
        
        # Overlay the PiP on the main clip
        return CompositeVideoClip([main_clip, pip_clip.set_position(pos)])
    
    @staticmethod
    def create_sliding_transition(clip1, clip2, duration=1.0, direction="left"):
        """
        Create a sliding transition between two clips
        
        Args:
            clip1: First video clip
            clip2: Second video clip
            duration: Duration of the transition in seconds
            direction: Direction of the slide ("left", "right", "up", "down")
            
        Returns:
            VideoClip with sliding transition
        """
        w, h = clip1.size
        
        # Ensure both clips have the same size
        clip2 = clip2.resize(width=w, height=h)
        
        # Define the slide function based on direction
        if direction == "left":
            def slide_pos(t):
                # t goes from 0 to duration
                # clip1 moves from (0,0) to (-w,0)
                # clip2 moves from (w,0) to (0,0)
                return [('center', 'center'), (w*(1-t/duration), 'center')]
        
        elif direction == "right":
            def slide_pos(t):
                return [('center', 'center'), (-w*(1-t/duration), 'center')]
        
        elif direction == "up":
            def slide_pos(t):
                return [('center', 'center'), ('center', h*(1-t/duration))]
        
        elif direction == "down":
            def slide_pos(t):
                return [('center', 'center'), ('center', -h*(1-t/duration))]
        
        else:
            # Default: left
            def slide_pos(t):
                return [('center', 'center'), (w*(1-t/duration), 'center')]
        
        # Create the transition clip
        last_frame_clip1 = clip1.to_ImageClip(clip1.duration)
        first_frame_clip2 = clip2.to_ImageClip(0)
        
        positions = lambda t: slide_pos(t)
        transition_clip = CompositeVideoClip([
            last_frame_clip1.set_position(positions(0)[0]),
            first_frame_clip2.set_position(positions(0)[1])
        ]).set_duration(duration)
        
        for t in np.linspace(0, duration, 20):
            pos = positions(t)
            transition_clip = CompositeVideoClip([
                last_frame_clip1.set_position(pos[0]),
                first_frame_clip2.set_position(pos[1])
            ]).set_duration(duration)
        
        # Concatenate the clips with the transition
        return concatenate_videoclips([
            clip1.subclip(0, clip1.duration - duration/2),
            transition_clip,
            clip2.subclip(duration/2)
        ], method="compose")
    
    @staticmethod
    def create_dynamic_text_effect(clip, text, font_size=50, color='white', start_time=0, end_time=None, effect="fade"):
        """
        Add animated text to a video clip
        
        Args:
            clip: VideoClip to add text to
            text: Text to display
            font_size: Size of the font
            color: Color of the text
            start_time: Time to start displaying the text
            end_time: Time to end displaying the text (defaults to clip end)
            effect: Animation effect ("fade", "typewriter", "slide_in")
            
        Returns:
            CompositeVideoClip with animated text
        """
        if end_time is None:
            end_time = clip.duration
            
        duration = end_time - start_time
        
        # Create the text clip
        txt_clip = TextClip(text, font='Arial', fontsize=font_size, color=color)
        txt_clip = txt_clip.set_position('center').set_duration(duration)
        
        # Apply the animation effect
        if effect == "fade":
            txt_clip = txt_clip.fadein(min(1, duration/4)).fadeout(min(1, duration/4))
            
        elif effect == "typewriter":
            # Simulate typewriter effect by showing characters one by one
            char_clips = []
            for i, char in enumerate(text):
                char_clip = TextClip(char, font='Arial', fontsize=font_size, color=color)
                char_width = char_clip.w
                
                # Position characters side by side
                x_pos = (i * char_width) - (len(text) * char_width / 2)
                
                # Make each character appear with a delay
                char_delay = min(0.1, duration / (len(text) * 2))
                char_start = i * char_delay
                
                char_clip = (char_clip
                             .set_position(lambda t: (x_pos, 0))
                             .set_start(char_start)
                             .set_duration(duration - char_start))
                char_clips.append(char_clip)
                
            txt_clip = CompositeVideoClip(char_clips).set_position('center')
            
        elif effect == "slide_in":
            # Slide in from the right
            w = clip.w
            slide_duration = min(1, duration/3)
            
            def slide_pos(t):
                if t < slide_duration:
                    # Slide in during the first part
                    x_pos = w - (w * t / slide_duration)
                    return (x_pos, 'center')
                else:
                    # Stay in center for the rest
                    return ('center', 'center')
                    
            txt_clip = txt_clip.set_position(lambda t: slide_pos(t))
        
        # Add the text clip at the specified time
        txt_clip = txt_clip.set_start(start_time)
        
        return CompositeVideoClip([clip, txt_clip])
    
    @staticmethod
    def animate_3d_object(clip, object_type="money", duration=5, pattern="floating"):
        """
        Add an animated 3D object (money, HVAC, etc.) to the clip
        This is a simulated effect using MoviePy - in production, you'd use a real 3D engine
        
        Args:
            clip: Base video clip
            object_type: Type of object to animate ("money", "hvac", "building")
            duration: Duration of the animation
            pattern: Movement pattern ("floating", "raining", "rotating")
            
        Returns:
            CompositeVideoClip with the animated object
        """
        # In a production app, you'd use actual 3D models and rendering
        # For this example, we'll simulate it with basic image manipulations
        
        # Create a colored rectangle as a placeholder for the 3D object
        w, h = clip.size
        obj_w, obj_h = int(w * 0.2), int(h * 0.2)
        
        if object_type == "money":
            color = (0, 155, 0)  # Green for money
        elif object_type == "hvac":
            color = (100, 100, 100)  # Gray for HVAC
        else:
            color = (200, 100, 0)  # Orange for other objects
            
        obj_clip = ColorClip(size=(obj_w, obj_h), color=color)
        obj_clip = obj_clip.set_duration(duration)
        
        # Apply animation pattern
        if pattern == "floating":
            # Floating up and down with slight rotation
            def float_pos(t):
                # Oscillate up and down
                y_pos = h * 0.5 + np.sin(t * 2) * (h * 0.1)
                # Move horizontally
                x_pos = w * 0.5 + np.sin(t * 1.5) * (w * 0.1)
                return (x_pos, y_pos)
                
            obj_clip = obj_clip.set_position(lambda t: float_pos(t))
            # Add slight rotation
            obj_clip = obj_clip.fx(vfx.rotate, lambda t: np.sin(t*3) * 10)
            
        elif pattern == "raining":
            # Multiple objects raining down
            obj_clips = []
            
            for i in range(5):  # Create 5 copies
                # Random horizontal position
                x_pos = np.random.uniform(0, w)
                # Random start time
                start_time = np.random.uniform(0, duration * 0.7)
                # Random fall speed
                fall_speed = np.random.uniform(50, 100)
                
                def rain_pos(t, x_start, speed):
                    # Fall from top to bottom
                    y_pos = t * speed - obj_h
                    if y_pos > h:
                        y_pos = -obj_h  # Reset to top when it goes below screen
                    return (x_start, y_pos)
                
                obj_copy = obj_clip.copy()
                obj_copy = obj_copy.set_position(lambda t: rain_pos(t, x_pos, fall_speed))
                obj_copy = obj_copy.set_start(start_time).set_duration(duration - start_time)
                obj_clips.append(obj_copy)
            
            # Combine all raining objects with the main clip
            return CompositeVideoClip([clip] + obj_clips)
            
        elif pattern == "rotating":
            # Rotate around a central point
            center_x, center_y = w/2, h/2
            radius = min(w, h) * 0.3
            
            def rotate_pos(t):
                angle = t * 2 * np.pi / 5  # Complete rotation every 5 seconds
                x_pos = center_x + radius * np.cos(angle)
                y_pos = center_y + radius * np.sin(angle)
                return (x_pos, y_pos)
                
            obj_clip = obj_clip.set_position(lambda t: rotate_pos(t))
            # Add rotation to the object itself
            obj_clip = obj_clip.fx(vfx.rotate, lambda t: t * 360 / 5)
        
        # Composite the object with the main clip
        return CompositeVideoClip([clip, obj_clip]) 