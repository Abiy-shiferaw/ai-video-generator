# AI Video Generator

An application for generating professional videos and animated ads from text descriptions or images using AI, with optional AI voiceover capabilities.

## Features

- **Image to Video**: Transform static images into dynamic videos with customizable effects, styles, and duration
- **Text to Video**: Create videos directly from text prompts with various style options
- **Professional Ad Creator**: Generate sleek, non-AI-looking animated advertisements with brand customization
- **AI Voiceover**: Add AI-generated voiceovers to your videos
- **Custom Voice Training**: Train the system on your voice for personalized voiceovers

## Professional Ad Creator

Our new Professional Ad Creator feature allows you to:

- Create high-quality, professional-looking animated ads
- Customize your brand colors, animation style, and visual aesthetic
- Choose from multiple ad templates (product showcase, testimonial, explainer, etc.)
- Add voiceover using AI voice cloning technology
- Generate ads that don't look AI-generated but have a polished, professional appearance

### Ad Templates

- **Product Showcase**: Highlight product features and benefits
- **Testimonial**: Feature customer testimonials in an engaging format
- **Explainer**: Educational videos explaining your product or service
- **Storytelling**: Narrative-driven advertising that tells a compelling story
- **Corporate**: Professional messaging with strong brand emphasis

### Animation Styles

- **Sleek & Smooth**: Clean, professional animations with smooth transitions
- **Motion Graphics**: Dynamic motion graphics with modern design elements
- **Isometric**: 3D isometric animations with depth and perspective
- **2D Character**: Character-based animations with personality
- **Animated Infographics**: Data-driven visualizations that inform and engage

## Tech Stack

- **Frontend**: Next.js, React, Tailwind CSS
- **Backend**: Python, Flask, OpenAI API, DALL-E API, ElevenLabs API
- **Processing**: MoviePy, FFmpeg, Google Text-to-Speech

## Setup Instructions

### Backend

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ```

4. Start the server:
   ```
   python app.py
   ```

### Frontend

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm run dev
   ```

## License

[MIT License](LICENSE) 