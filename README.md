# AI Video Generator

An application for generating professional videos and animated ads using AI, optimized for creating engaging social media content.

## Core Features

- **Professional Ad Creator**: Generate sleek, professional-looking animated advertisements with brand customization, perfect for social media marketing.
- **Advanced Motion Video**: Create dynamic AI-generated videos with real motion and professional effects using cutting-edge AI technology.
- **AI Voiceover**: Add professional AI-generated voiceovers to your videos with voice customization options.

## Ad Creator Capabilities

The Professional Ad Creator allows you to create high-quality, engaging advertising content for:

- **Product Showcases**: Highlight product features with professional animations and transitions
- **Brand Promotion**: Build brand awareness with custom colors, logos, and messaging
- **Social Media Campaigns**: Generate content optimized for various social platforms

## Advanced Motion Video Features

Our Advanced Motion Video feature leverages cutting-edge AI technology:

- **AI-Powered Motion**: Generate videos with realistic motion using RunwayML technology
- **Professional Effects**: Apply cinematic effects like Ken Burns, 3D rotation, and dynamic zoom
- **Custom Animations**: Add animated text and graphics with professional transitions

## Quick Setup

### Backend

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file and add your API keys:
   ```
   OPENAI_API_KEY=your_openai_key
   ELEVEN_LABS_API_KEY=your_elevenlabs_key
   RUNWAYML_API_KEY=your_runwayml_key
   PEXELS_API_KEY=your_pexels_key
   STABILITY_API_KEY=your_stability_key
   ```

4. Start the backend server:
   ```
   python app.py
   ```

### Frontend

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install the required dependencies:
   ```
   npm install
   ```

3. Start the frontend development server:
   ```
   npm run dev
   ```

4. Open your browser and go to `http://localhost:3000`

## Usage

1. Choose the feature you want to use (Professional Ad Creator or Advanced Motion Video)
2. Enter your content details and preferences
3. Generate and download your professional video

## Technologies

- **AI Video Generation**: RunwayML, Stability AI, OpenAI DALL-E
- **Frontend**: Next.js, React, Tailwind CSS
- **Backend**: Python, Flask
- **Voice Synthesis**: Eleven Labs 