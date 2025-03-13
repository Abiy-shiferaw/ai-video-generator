class VideoRecommender:
    """
    Recommends the best video generation source based on the prompt and content type.
    """
    
    @staticmethod
    def recommend_source(prompt, content_type):
        """
        Recommend the best video source based on the prompt and detected content type.
        
        Args:
            prompt (str): The text prompt describing the video
            content_type (str): The detected content type (testimonial, commercial, etc.)
            
        Returns:
            str: Recommended video source (hybrid, runway, stability, pexels)
        """
        prompt = prompt.lower()
        
        # For testimonials, prefer stock video or hybrid approach
        if content_type == "testimonial":
            if len(prompt) > 300:  # Complex testimonial
                return "hybrid"
            else:
                return "pexels"
                
        # For cinematic content, prefer AI generation
        if content_type == "cinematic":
            return "runway"  # RunwayML tends to be better for cinematic content
            
        # For commercials, use hybrid approach for better quality
        if content_type == "commercial":
            return "hybrid"
            
        # For explainers, depends on complexity
        if content_type == "explainer":
            if "3d" in prompt or "animation" in prompt:
                return "stability"
            else:
                return "hybrid"
        
        # Default to hybrid for best results
        return "hybrid" 