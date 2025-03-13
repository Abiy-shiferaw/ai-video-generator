class ContentAnalyzer:
    """
    Analyzes the content of a prompt to determine what type of video it describes.
    """
    
    def __init__(self):
        # Initialize any resources needed for content analysis
        self.video_types = {
            "testimonial": ["testimony", "testimonial", "review", "experience", "talking head"],
            "commercial": ["advertisement", "commercial", "promotion", "marketing", "product"],
            "explainer": ["explain", "explainer", "how to", "tutorial", "educational", "guide"],
            "cinematic": ["cinematic", "film", "movie", "dramatic", "storytelling"]
        }
    
    def detect_content_type(self, prompt):
        """
        Detect the primary type of video based on the prompt content.
        
        Args:
            prompt (str): The text prompt describing the video
            
        Returns:
            dict: Dictionary with primary_type and scores for each content type
        """
        # Simple keyword-based detection for now
        prompt = prompt.lower()
        scores = {}
        
        # Calculate scores for each type
        for content_type, keywords in self.video_types.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in prompt:
                    score += 1
            scores[content_type] = score / len(keywords) if keywords else 0
            
        # Get the primary type (highest score)
        primary_type = max(scores, key=scores.get) if scores else "commercial"
        
        # If all scores are 0, default to commercial
        if all(score == 0 for score in scores.values()):
            primary_type = "commercial"
            
        return {
            "primary_type": primary_type,
            "scores": scores
        } 