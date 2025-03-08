# AI Video Generator

An application for generating videos from text descriptions or images using AI, with optional AI voiceover capabilities.

## Features

- **Image to Video**: Transform static images into dynamic videos with customizable effects, styles, and duration
- **Text to Video**: Create videos directly from text prompts with various style options
- **AI Voiceover**: Add AI-generated voiceovers to your videos
- **Custom Voice Training**: Train the system on your voice for personalized voiceovers

## Tech Stack

- **Frontend**: Next.js, React, Tailwind CSS
- **Backend**: Python, Flask, OpenAI API, DEEPA API, ElevenLabs API
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

3. Start the server:
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

## Environment Variables

You'll need to set up the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key
- `DEEPA_API_KEY`: Your DEEPA API key for text-to-video generation
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key for voice cloning and generation

## License

[MIT License](LICENSE) 