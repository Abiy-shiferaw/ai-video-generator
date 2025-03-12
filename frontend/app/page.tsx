'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion } from 'framer-motion';
import axios from 'axios';
import { FaUpload, FaVideo, FaVolumeUp, FaSpinner, FaCheck, FaMicrophone, FaStop, FaImages, FaTrash, FaBullhorn, FaPalette, FaBriefcase } from 'react-icons/fa';

interface Template {
  id: string;
  name: string;
  description: string;
}

interface TemplatesResponse {
  templates: Template[];
}

interface Effect {
  id: string;
  name: string;
  description: string;
}

interface JobStatus {
  status: string;
  progress: number;
  result?: {
    script: string;
    effects: string[];
    video_path: string;
    used_custom_model?: boolean;
    used_custom_voice?: boolean;
  };
  error?: string;
  estimated_time_remaining?: number;
}

interface UploadResponse {
  message: string;
  filepath: string;
  face_detected?: boolean;
}

interface VideoResponse {
  message: string;
  job_id: string;
  status: string;
}

interface VoiceFile {
  id: string;
  name: string;
  url: string;
}

interface VoiceUploadResponse {
  success: boolean;
  voice_id: string;
  filename: string;
  url: string;
  error?: string;
}

interface TrainingImage {
  id: string;
  file: File;
  preview: string;
  type: 'image' | 'video';
}

interface TrainingModelResponse {
  success: boolean;
  model_id: string;
  files_count: number;
  model: {
    id: string;
    name: string;
    created_at: string;
    status: string;
    training_files: Array<{
      id: string;
      filename: string;
      type: string;
      url: string;
    }>;
  };
  error?: string;
}

interface TrainingStatusResponse {
  success: boolean;
  model: {
    id: string;
    name: string;
    created_at: string;
    status: string;
  };
  error?: string;
}

export default function Home() {
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [uploadedFilePath, setUploadedFilePath] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [addVoiceover, setAddVoiceover] = useState(false);
  const [videoStyle, setVideoStyle] = useState('casual');
  const [videoDuration, setVideoDuration] = useState(15);
  const [uploadedVoices, setUploadedVoices] = useState<VoiceFile[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [isTrainingMode, setIsTrainingMode] = useState(false);
  const [trainingImages, setTrainingImages] = useState<TrainingImage[]>([]);
  const [trainingInProgress, setTrainingInProgress] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState(0);
  const [modelId, setModelId] = useState<string | null>(null);
  const [isTextToVideoMode, setIsTextToVideoMode] = useState(false);
  const [textPrompt, setTextPrompt] = useState('');
  const [isAdMode, setIsAdMode] = useState(false);
  const [adTemplate, setAdTemplate] = useState('product');
  const [adStyle, setAdStyle] = useState('professional');
  const [adDuration, setAdDuration] = useState(30);
  const [adText, setAdText] = useState('');
  const [brandName, setBrandName] = useState('');
  const [tagline, setTagline] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [colorScheme, setColorScheme] = useState('blue');
  const [animationStyle, setAnimationStyle] = useState('sleek');
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch templates when component mounts
  useEffect(() => {
    async function fetchTemplates() {
      try {
        console.log('Fetching templates...');
        const response = await axios.get<TemplatesResponse>('http://localhost:8000/api/templates');
        console.log('Templates fetched:', response.data.templates);
        setTemplates(response.data.templates);
      } catch (err) {
        console.error('Error fetching templates:', err);
      }
    }
    
    fetchTemplates();
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png']
    },
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      const file = acceptedFiles[0];
      setPhoto(file);
      setPreview(URL.createObjectURL(file));
      setError(null);
    }
  });

  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (jobId && jobStatus?.status !== 'completed' && jobStatus?.status !== 'failed') {
      interval = setInterval(async () => {
        try {
          const response = await axios.get<JobStatus>(`http://localhost:8000/api/status/${jobId}`);
          setJobStatus(response.data);
          
          if (response.data.status === 'completed' || response.data.status === 'failed') {
            clearInterval(interval);
            setLoading(false);
            if (response.data.status === 'failed') {
              setError(response.data.error || 'Video generation failed');
            }
          }
        } catch (err) {
          console.error('Error checking job status:', err);
          clearInterval(interval);
          setLoading(false);
          setError('Failed to check video generation status');
        }
      }, 2000);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [jobId, jobStatus?.status]);

  const handleGenerateVideo = async () => {
    if (!photo) {
      setError('Please upload a photo first');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // First, upload the photo
      const formData = new FormData();
      formData.append('file', photo);
      
      const uploadResponse = await axios.post<UploadResponse>('http://localhost:8000/api/upload-photo', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log('Upload response:', uploadResponse.data);

      if (uploadResponse.data.face_detected === false) {
        throw new Error('No face detected in the image');
      }

      if (!uploadResponse.data.filepath) {
        throw new Error('No filepath returned from server');
      }

      setUploadedFilePath(uploadResponse.data.filepath);

      // Then, generate the video
      const videoResponse = await axios.post<VideoResponse>('http://localhost:8000/api/generate-video', {
        style: videoStyle,
        duration: videoDuration,
        effects: [],
        background: null,
        image_path: uploadResponse.data.filepath, // Use the filepath returned from the server
        template: selectedTemplate,
        add_voiceover: addVoiceover,
        voice_id: selectedVoice,
        model_id: modelId // Include model ID if available from training
      });

      setJobId(videoResponse.data.job_id);
      setJobStatus({
        status: 'initializing',
        progress: 0
      });

    } catch (err) {
      console.error('Error during video generation:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
      setLoading(false);
    }
  };

  const handleTextToVideoGeneration = async () => {
    if (!textPrompt) {
      setError('Please enter a text prompt to generate a video');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // Define the response type
      interface TextToVideoResponse {
        success: boolean;
        job_id: string;
        status: string;
        error?: string;
      }
      
      // Send request to generate video from text
      const response = await axios.post<TextToVideoResponse>('http://localhost:8000/api/generate-video-from-text', {
        prompt: textPrompt,
        duration: videoDuration,
        style: videoStyle,
        voice_id: selectedVoice
      });
      
      if (response.data.success) {
        // Get the job ID
        setJobId(response.data.job_id);
        
        // Start checking status
        startCheckingStatus(response.data.job_id);
      } else {
        setError(response.data.error || 'Failed to initiate video generation');
        setLoading(false);
      }
    } catch (error) {
      console.error('Error generating video from text:', error);
      setError('Error generating video. Please try again.');
      setLoading(false);
    }
  };

  // Voice recording functions
  const startRecording = async () => {
    audioChunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioBlob(audioBlob);
        
        // Upload the recorded audio
        uploadVoiceRecording(audioBlob);
      };
      
      mediaRecorder.start();
      setIsRecording(true);
      
      // Start timer
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime(prevTime => prevTime + 1);
      }, 1000);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Unable to access your microphone. Please check permissions.');
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      
      // Stop all audio tracks
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };
  
  const uploadVoiceRecording = async (blob: Blob) => {
    const formData = new FormData();
    formData.append('voice', blob, `recording_${Date.now()}.wav`);
    
    try {
      const response = await axios.post<VoiceUploadResponse>('http://localhost:8000/api/upload-voice', formData);
      if (response.data.success) {
        const newVoice = {
          id: response.data.voice_id,
          name: response.data.filename,
          url: response.data.url
        };
        setUploadedVoices(prev => [...prev, newVoice]);
        setSelectedVoice(newVoice.id);
      }
    } catch (error) {
      console.error('Error uploading voice recording:', error);
    }
  };
  
  const handleVoiceUpload = async (files: File[]) => {
    if (files.length === 0) return;
    
    const formData = new FormData();
    formData.append('voice', files[0]);
    
    try {
      const response = await axios.post<VoiceUploadResponse>('http://localhost:8000/api/upload-voice', formData);
      if (response.data.success) {
        const newVoice = {
          id: response.data.voice_id,
          name: response.data.filename,
          url: response.data.url
        };
        setUploadedVoices(prev => [...prev, newVoice]);
        setSelectedVoice(newVoice.id);
      }
    } catch (error) {
      console.error('Error uploading voice file:', error);
    }
  };
  
  const { getRootProps: getVoiceRootProps, getInputProps: getVoiceInputProps } = useDropzone({
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a']
    },
    maxFiles: 1,
    onDrop: handleVoiceUpload
  });

  // Function to handle training images upload
  const handleTrainingImagesUpload = (acceptedFiles: File[]) => {
    const newImages = acceptedFiles.map(file => ({
      id: `img_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      file,
      preview: URL.createObjectURL(file),
      type: file.type.startsWith('image/') ? 'image' : 'video' as 'image' | 'video'
    }));
    
    setTrainingImages(prev => [...prev, ...newImages]);
  };
  
  // Remove a training image
  const removeTrainingImage = (id: string) => {
    setTrainingImages(prev => prev.filter(img => img.id !== id));
  };
  
  // Update the startTraining function to use the real API
  const startTraining = async () => {
    if (trainingImages.length < 3) {
      setError('Please upload at least 3 images or videos for training');
      return;
    }
    
    setTrainingInProgress(true);
    setError(null);
    
    try {
      // First, upload all images
      const formData = new FormData();
      trainingImages.forEach(img => {
        formData.append('files[]', img.file);
        formData.append('types[]', img.type);
      });
      
      // Step 1: Upload files for training
      const uploadResponse = await axios.post<TrainingModelResponse>(
        'http://localhost:8000/api/upload-training', 
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      if (!uploadResponse.data.success) {
        throw new Error(uploadResponse.data.error || 'Failed to upload training files');
      }
      
      setTrainingProgress(30);
      const modelId = uploadResponse.data.model_id;
      
      // Step 2: Start the training process
      const startTrainingResponse = await axios.post<TrainingModelResponse>(
        'http://localhost:8000/api/training/start',
        { model_id: modelId }
      );
      
      if (!startTrainingResponse.data.success) {
        throw new Error(startTrainingResponse.data.error || 'Failed to start training');
      }
      
      setTrainingProgress(50);
      
      // Step 3: Poll for training status
      let isCompleted = false;
      let attempts = 0;
      
      while (!isCompleted && attempts < 30) { // Limit to 30 attempts (5 minutes with 10s interval)
        await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds between checks
        
        const statusResponse = await axios.get<TrainingStatusResponse>(
          `http://localhost:8000/api/training/status/${modelId}`
        );
        
        if (!statusResponse.data.success) {
          console.error('Error checking training status:', statusResponse.data.error);
          continue;
        }
        
        const status = statusResponse.data.model.status;
        
        // Update progress based on status
        switch (status) {
          case 'preprocessing':
            setTrainingProgress(60);
            break;
          case 'feature_extraction':
            setTrainingProgress(70);
            break;
          case 'training':
            setTrainingProgress(80);
            break;
          case 'finetuning':
            setTrainingProgress(90);
            break;
          case 'completed':
            setTrainingProgress(100);
            setModelId(modelId);
            isCompleted = true;
            break;
          case 'failed':
            throw new Error('Training failed. Please try again.');
        }
        
        attempts++;
      }
      
      if (!isCompleted) {
        throw new Error('Training timed out. The process may still be running in the background.');
      }
      
      setTrainingInProgress(false);
      
    } catch (error) {
      console.error('Error training model:', error);
      setError(error instanceof Error ? error.message : 'Failed to train custom model');
      setTrainingInProgress(false);
    }
  };

  // Update dropdown options to include voice selection
  const { getRootProps: getTrainingRootProps, getInputProps: getTrainingInputProps } = useDropzone({
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png'],
      'video/*': ['.mp4', '.mov', '.avi']
    },
    onDrop: handleTrainingImagesUpload
  });

  // Add a utility function to format time in minutes and seconds
  const formatTime = (seconds: number | undefined): string => {
    if (!seconds) return '00:00';
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Update the startCheckingStatus function to handle the countdown timer
  const startCheckingStatus = async (jobId: string) => {
    const checkStatus = async () => {
      try {
        const response = await axios.get<JobStatus>(`http://localhost:8000/api/status/${jobId}`);
        setJobStatus(response.data);
        
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          setLoading(false);
          
          // If completed, log information about custom voice/model usage
          if (response.data.status === 'completed' && response.data.result) {
            console.log('Video generated successfully!');
            if (response.data.result.used_custom_model) {
              console.log('Using your custom trained model for personalization.');
            }
            if (response.data.result.used_custom_voice) {
              console.log('Using your custom voice for narration.');
            }
          }
          
          return;
        }
        
        // Continue checking status
        setTimeout(checkStatus, 2000);
      } catch (error) {
        console.error('Error checking job status:', error);
        setLoading(false);
      }
    };
    
    // Start checking immediately
    checkStatus();
  };

  // Add new function for generating professional ad
  const handleAdGeneration = async () => {
    if (!adText) {
      setError('Please enter ad content');
      return;
    }
    
    setLoading(true);
    setError(null);
    setJobStatus(null);
    
    try {
      const response = await axios.post<{ success: boolean; job_id: string; status: string }>('http://localhost:8000/api/generate-ad', {
        prompt: adText,
        brand_name: brandName,
        tagline: tagline,
        target_audience: targetAudience,
        duration: adDuration,
        style: adStyle,
        template: adTemplate,
        color_scheme: colorScheme,
        animation_style: animationStyle,
        voice_id: selectedVoice,
      });

      if (response.data.success) {
        setJobId(response.data.job_id);
        // Start polling for job status
        const checkStatus = async () => {
          try {
            const statusResponse = await axios.get<JobStatus>(`http://localhost:8000/api/status/${response.data.job_id}`);
            setJobStatus(statusResponse.data);
            
            if (statusResponse.data.status === 'completed' || statusResponse.data.status === 'failed') {
              setLoading(false);
            }
          } catch (err) {
            console.error('Error checking job status:', err);
            setLoading(false);
            setError('Failed to check ad generation status');
          }
        };
        
        // Initial check
        checkStatus();
        
        // Set up interval to check every 2 seconds
        const interval = setInterval(checkStatus, 2000);
        
        // Clear interval after 5 minutes (300000 ms) to prevent infinite polling
        setTimeout(() => {
          clearInterval(interval);
          if (loading) {
            setLoading(false);
            setError('Ad generation is taking longer than expected. Please check back later.');
          }
        }, 300000);
      } else {
        setError('Failed to generate ad');
        setLoading(false);
      }
    } catch (err: any) {
      console.error('Error:', err);
      setError(err.message || 'An error occurred');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100 to-purple-100 py-12 px-4">
      <div className="max-w-6xl mx-auto bg-white rounded-xl shadow-xl overflow-hidden">
        <div className="p-8">
          <div className="flex justify-center mb-10">
            <h1 className="text-4xl font-bold text-center bg-clip-text text-transparent bg-gradient-to-r from-purple-600 to-indigo-600">
              AI Video Generator
            </h1>
          </div>
          
          <div className="mb-8 flex justify-center space-x-4">
            <button
              onClick={() => {
                setIsTrainingMode(false);
                setIsTextToVideoMode(false);
                setIsAdMode(false);
              }}
              className={`px-4 py-2 rounded-lg ${!isTrainingMode && !isTextToVideoMode && !isAdMode ? 'bg-purple-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            >
              Image to Video
            </button>
            <button
              onClick={() => {
                setIsTrainingMode(false);
                setIsTextToVideoMode(true);
                setIsAdMode(false);
              }}
              className={`px-4 py-2 rounded-lg ${isTextToVideoMode ? 'bg-purple-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            >
              Text to Video
            </button>
            <button
              onClick={() => {
                setIsTrainingMode(true);
                setIsTextToVideoMode(false);
                setIsAdMode(false);
              }}
              className={`px-4 py-2 rounded-lg ${isTrainingMode ? 'bg-purple-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            >
              Train Custom Model
            </button>
            <button
              onClick={() => {
                setIsTrainingMode(false);
                setIsTextToVideoMode(false);
                setIsAdMode(true);
              }}
              className={`px-4 py-2 rounded-lg ${isAdMode ? 'bg-purple-600 text-white' : 'bg-gray-200 text-gray-700'}`}
            >
              Professional Ad Creator
            </button>
          </div>
          
          {isTextToVideoMode ? (
            // Text-to-Video Mode UI
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gray-800 rounded-lg p-6 mb-8"
            >
              <h2 className="text-2xl font-semibold mb-4">Generate Video from Text</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-gray-300 mb-2">Describe your video</label>
                  <textarea
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg p-4 text-white"
                    rows={4}
                    placeholder="Describe what you want to see in your video, including subjects, environment, actions, color scheme, etc."
                    value={textPrompt}
                    onChange={(e) => setTextPrompt(e.target.value)}
                  ></textarea>
                </div>
                
                <div className="flex flex-col md:flex-row md:space-x-4 space-y-4 md:space-y-0">
                  <div className="w-full md:w-1/2">
                    <label className="block text-gray-300 mb-2">Visual Style</label>
                    <select 
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                      value={videoStyle}
                      onChange={(e) => setVideoStyle(e.target.value)}
                    >
                      <option value="casual">Casual/Natural</option>
                      <option value="cinematic">Cinematic</option>
                      <option value="professional">Professional/Corporate</option>
                      <option value="creative">Creative/Artistic</option>
                      <option value="vintage">Vintage/Retro</option>
                    </select>
                  </div>
                  
                  <div className="w-full md:w-1/2">
                    <label className="block text-gray-300 mb-2">Duration (seconds)</label>
                    <div className="flex items-center">
                      <input
                        type="range"
                        min="5"
                        max="30"
                        value={videoDuration}
                        onChange={(e) => setVideoDuration(parseInt(e.target.value))}
                        className="w-full"
                      />
                      <div className="flex justify-between text-gray-400 text-sm ml-2">
                        <span>{videoDuration}s</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="voiceover-text"
                    checked={addVoiceover}
                    onChange={(e) => setAddVoiceover(e.target.checked)}
                    className="mr-2"
                  />
                  <label htmlFor="voiceover-text" className="text-gray-300">
                    Add AI Voiceover
                  </label>
                </div>
              </div>
            </motion.div>
          ) : null}
          
          {isTrainingMode ? (
            // Training Mode UI
            <div className="bg-white p-6 rounded-lg shadow-md mb-8">
              <h2 className="text-xl font-semibold mb-4">Train Your Custom Model</h2>
              
              <p className="mb-4 text-gray-700">
                Upload multiple photos and videos of yourself to create a personalized model that looks and moves like you.
                <br/>
                <span className="text-sm">Recommended: Upload at least 10 varied images and 2-3 short video clips for best results.</span>
              </p>
              
              {/* Training Images Upload */}
              <div 
                {...getTrainingRootProps()} 
                className="border-2 border-dashed border-gray-300 rounded-lg p-6 mb-4 text-center cursor-pointer hover:bg-gray-50"
              >
                <input {...getTrainingInputProps()} />
                <FaImages className="text-3xl mx-auto mb-2 text-gray-400" />
                <p>Drag and drop images and videos here, or click to select</p>
                <p className="text-sm text-gray-500 mt-1">Supports JPG, PNG, MP4, MOV</p>
              </div>
              
              {/* Previews */}
              {trainingImages.length > 0 && (
                <div className="mt-4 mb-6">
                  <h3 className="font-medium mb-2">Uploaded Files ({trainingImages.length}):</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                    {trainingImages.map(img => (
                      <div key={img.id} className="relative">
                        {img.type === 'image' ? (
                          <img 
                            src={img.preview} 
                            className="h-24 w-24 object-cover rounded-md" 
                            alt="Preview" 
                          />
                        ) : (
                          <div className="h-24 w-24 bg-gray-200 rounded-md flex items-center justify-center">
                            <FaVideo className="text-gray-500" />
                          </div>
                        )}
                        <button 
                          onClick={() => removeTrainingImage(img.id)}
                          className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1"
                        >
                          <FaTrash size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Training Button */}
              {!modelId ? (
                <button
                  onClick={startTraining}
                  disabled={trainingImages.length < 3 || trainingInProgress}
                  className={`px-6 py-3 rounded-lg text-white font-semibold w-full ${
                    trainingImages.length < 3 || trainingInProgress
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-green-600 hover:bg-green-700'
                  }`}
                >
                  {trainingInProgress ? (
                    <span className="flex items-center justify-center">
                      <FaSpinner className="animate-spin mr-2" /> Training Model... {trainingProgress}%
                    </span>
                  ) : (
                    'Start Training'
                  )}
                </button>
              ) : (
                <div className="bg-green-50 border border-green-200 p-4 rounded-lg text-center">
                  <p className="text-green-800 font-medium">Model trained successfully!</p>
                  <p className="text-sm text-green-700">Your custom model is ready to use. You can now generate videos.</p>
                </div>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Photo Upload Section */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gray-800 rounded-lg p-6"
              >
                <h2 className="text-2xl font-semibold mb-4">Upload Your Photo</h2>
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                    ${isDragActive ? 'border-blue-500 bg-blue-500/10' : 'border-gray-600 hover:border-blue-500'}`}
                >
                  <input {...getInputProps()} />
                  {preview ? (
                    <img
                      src={preview}
                      alt="Preview"
                      className="max-w-full h-auto rounded-lg"
                    />
                  ) : (
                    <div className="space-y-4">
                      <p className="text-gray-400">
                        Drag and drop your photo here, or click to select
                      </p>
                      <p className="text-sm text-gray-500">
                        Supported formats: JPEG, JPG, PNG
                      </p>
                    </div>
                  )}
                </div>

                {/* Video Settings */}
                <div className="mt-6">
                  <h3 className="text-xl font-semibold mb-4">Video Settings</h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-gray-300 mb-2">Style</label>
                      <select 
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                        value={videoStyle}
                        onChange={(e) => setVideoStyle(e.target.value)}
                      >
                        <option value="casual">Casual</option>
                        <option value="professional">Professional</option>
                        <option value="energetic">Energetic</option>
                        <option value="cinematic">Cinematic</option>
                        <option value="dramatic">Dramatic</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-gray-300 mb-2">Duration (seconds)</label>
                      <input 
                        type="range"
                        min="5"
                        max="60"
                        step="5"
                        value={videoDuration}
                        onChange={(e) => setVideoDuration(parseInt(e.target.value))}
                        className="w-full"
                      />
                      <div className="flex justify-between text-gray-400 text-sm">
                        <span>5s</span>
                        <span>{videoDuration}s</span>
                        <span>60s</span>
                      </div>
                    </div>

                    <div>
                      <label className="block text-gray-300 mb-2">Template</label>
                      <select 
                        className="w-full bg-gray-700 border border-gray-600 rounded-lg p-2 text-white"
                        value={selectedTemplate || ''}
                        onChange={(e) => setSelectedTemplate(e.target.value || null)}
                      >
                        <option value="">No Template (Custom)</option>
                        {templates.map(template => (
                          <option key={template.id} value={template.id}>
                            {template.name} - {template.description}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="voiceover"
                        checked={addVoiceover}
                        onChange={(e) => setAddVoiceover(e.target.checked)}
                        className="mr-2"
                      />
                      <label htmlFor="voiceover" className="text-gray-300">
                        Add AI Voiceover from Generated Script
                      </label>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Voice Upload Section */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-gray-800 rounded-lg p-6"
              >
                <h2 className="text-2xl font-semibold mb-4">Add Your Voice</h2>
                <div className="space-y-4">
                  <div {...getVoiceRootProps()} className="border-2 border-dashed border-gray-600 rounded-lg p-6 mb-4 text-center cursor-pointer hover:bg-gray-700">
                    <input {...getVoiceInputProps()} />
                    <FaVolumeUp className="text-3xl mx-auto mb-2 text-gray-400" />
                    <p>Drag and drop a voice recording here, or click to select</p>
                    <p className="text-sm text-gray-500 mt-1">Supports MP3, WAV (1-3 minutes recommended)</p>
                  </div>
                  
                  <div className="mt-4 mb-4">
                    <h3 className="font-medium mb-2">Or record your voice directly:</h3>
                    <div className="flex items-center space-x-4">
                      {isRecording ? (
                        <button 
                          onClick={stopRecording}
                          className="bg-red-600 text-white px-4 py-2 rounded-lg flex items-center"
                        >
                          <FaStop className="mr-2" /> Stop Recording ({recordingTime}s)
                        </button>
                      ) : (
                        <button 
                          onClick={startRecording}
                          className="bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center"
                        >
                          <FaMicrophone className="mr-2" /> Start Recording
                        </button>
                      )}
                    </div>
                  </div>
                  
                  {/* Voice Selection */}
                  {uploadedVoices.length > 0 && (
                    <div className="mt-4">
                      <h3 className="font-medium mb-2">Select voice to use:</h3>
                      <select 
                        className="w-full p-2 border border-gray-300 rounded-md"
                        value={selectedVoice || ''}
                        onChange={(e) => setSelectedVoice(e.target.value)}
                      >
                        <option value="">Default AI voice</option>
                        {uploadedVoices.map(voice => (
                          <option key={voice.id} value={voice.id}>
                            {voice.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              </motion.div>
            </div>
          )}

          {isAdMode && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="bg-white rounded-xl p-6 shadow-md"
            >
              <h2 className="text-2xl font-semibold text-purple-700 mb-6 flex items-center">
                <FaBullhorn className="mr-2" /> Professional Ad Creator
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Brand Name
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={(e) => setBrandName(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                    placeholder="Enter your brand name"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tagline
                  </label>
                  <input
                    type="text"
                    value={tagline}
                    onChange={(e) => setTagline(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                    placeholder="Enter your tagline"
                  />
                </div>
              </div>
              
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Ad Content
                </label>
                <textarea
                  value={adText}
                  onChange={(e) => setAdText(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 h-32"
                  placeholder="Describe your ad content, product benefits, and key selling points..."
                />
              </div>
              
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Target Audience
                </label>
                <input
                  type="text"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                  placeholder="Describe your target audience"
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Ad Template
                  </label>
                  <select
                    value={adTemplate}
                    onChange={(e) => setAdTemplate(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="product">Product Showcase</option>
                    <option value="testimonial">Testimonial</option>
                    <option value="explainer">Explainer</option>
                    <option value="storytelling">Storytelling</option>
                    <option value="corporate">Corporate</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Visual Style
                  </label>
                  <select
                    value={adStyle}
                    onChange={(e) => setAdStyle(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="professional">Professional/Corporate</option>
                    <option value="minimalist">Clean Minimalist</option>
                    <option value="vibrant">Vibrant & Bold</option>
                    <option value="luxury">Luxury & Premium</option>
                    <option value="playful">Playful & Fun</option>
                  </select>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <FaPalette className="inline mr-1" /> Color Scheme
                  </label>
                  <select
                    value={colorScheme}
                    onChange={(e) => setColorScheme(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="blue">Corporate Blue</option>
                    <option value="teal">Teal & Mint</option>
                    <option value="purple">Purple Gradient</option>
                    <option value="red">Vibrant Red</option>
                    <option value="dark">Dark Mode</option>
                    <option value="pastel">Soft Pastels</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Animation Style
                  </label>
                  <select
                    value={animationStyle}
                    onChange={(e) => setAnimationStyle(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                  >
                    <option value="sleek">Sleek & Smooth</option>
                    <option value="motion">Motion Graphics</option>
                    <option value="isometric">Isometric</option>
                    <option value="2d">2D Character</option>
                    <option value="infographic">Animated Infographics</option>
                  </select>
                </div>
              </div>
              
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Duration (seconds)
                </label>
                <div className="flex items-center">
                  <input
                    type="range"
                    min="15"
                    max="60"
                    step="5"
                    value={adDuration}
                    onChange={(e) => setAdDuration(parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <span className="ml-3 text-gray-700">{adDuration}s</span>
                </div>
              </div>
              
              <div className="mb-6">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="adVoiceover"
                    checked={addVoiceover}
                    onChange={(e) => setAddVoiceover(e.target.checked)}
                    className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                  />
                  <label htmlFor="adVoiceover" className="ml-2 block text-sm text-gray-700">
                    Add AI Voiceover
                  </label>
                </div>
                
                {addVoiceover && (
                  <div className="mt-4 ml-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select Voice
                    </label>
                    <select
                      value={selectedVoice || ""}
                      onChange={(e) => setSelectedVoice(e.target.value)}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                    >
                      <option value="">Select a voice</option>
                      {uploadedVoices.map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                    </select>
                    
                    {/* Voice recording UI (existing code) */}
                  </div>
                )}
              </div>
              
              <div className="flex justify-center mt-8">
                <button
                  onClick={handleAdGeneration}
                  disabled={!adText || loading}
                  className={`flex items-center justify-center px-6 py-3 rounded-lg text-white font-medium ${
                    !adText || loading
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700'
                  }`}
                >
                  {loading ? (
                    <>
                      <FaSpinner className="animate-spin mr-2" /> Generating Ad...
                    </>
                  ) : (
                    <>
                      <FaBullhorn className="mr-2" /> Generate Professional Ad
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          )}

          {/* Video Generation Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-gray-800 rounded-lg p-6 mt-8"
          >
            <h2 className="text-2xl font-semibold mb-4">Generate Your Video</h2>
            <div className="space-y-4">
              {isTextToVideoMode ? (
                <button
                  onClick={handleTextToVideoGeneration}
                  disabled={!textPrompt || loading}
                  className={`w-full py-3 px-4 rounded-lg font-semibold transition-colors
                    ${loading || !textPrompt
                      ? 'bg-gray-600 cursor-not-allowed'
                      : 'bg-blue-500 hover:bg-blue-600'}`}
                >
                  {loading ? 'Generating...' : 'Generate Video from Text'}
                </button>
              ) : (
                <button
                  onClick={handleGenerateVideo}
                  disabled={!photo || loading}
                  className={`w-full py-3 px-4 rounded-lg font-semibold transition-colors
                    ${loading || !photo
                      ? 'bg-gray-600 cursor-not-allowed'
                      : 'bg-blue-500 hover:bg-blue-600'}`}
                >
                  {loading ? 'Generating...' : 'Generate Video'}
                </button>
              )}

              {error && (
                <div className="bg-red-500/10 border border-red-500 text-red-500 p-4 rounded-lg">
                  {error}
                </div>
              )}

              {jobStatus && (
                <div className="space-y-4">
                  <div className="w-full bg-gray-700 rounded-full h-2.5">
                    <div
                      className="bg-blue-500 h-2.5 rounded-full transition-all duration-500"
                      style={{ width: `${jobStatus.progress}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-gray-400">
                    Status: {jobStatus.status.replace('_', ' ')}
                  </p>
                </div>
              )}

              {/* Right column: Preview and Results */}
              <div>
                {/* Processing Status */}
                {loading && jobStatus && (
                  <div className="bg-white p-6 rounded-lg shadow-md mb-8">
                    <h2 className="text-xl font-bold mb-4">Processing</h2>
                    <div className="mb-4">
                      <div className="flex justify-between mb-1">
                        <span className="text-sm font-medium">
                          {jobStatus.status === 'processing' ? 'Processing...' : jobStatus.status}
                        </span>
                        <span className="text-sm font-medium">{jobStatus.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div 
                          className="bg-blue-600 h-2.5 rounded-full" 
                          style={{ width: `${jobStatus.progress}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    {/* Estimated Time Countdown */}
                    {jobStatus.estimated_time_remaining !== undefined && jobStatus.estimated_time_remaining > 0 && (
                      <div className="text-center p-4 bg-gray-100 rounded-md">
                        <div className="flex justify-center items-center mb-2">
                          {/* Circular countdown timer */}
                          <div className="relative w-16 h-16">
                            <svg className="w-full h-full" viewBox="0 0 100 100">
                              {/* Background circle */}
                              <circle 
                                className="text-gray-200" 
                                strokeWidth="8" 
                                stroke="currentColor" 
                                fill="transparent" 
                                r="40" 
                                cx="50" 
                                cy="50" 
                              />
                              {/* Progress circle - stroke-dasharray is 2*PI*r, stroke-dashoffset decreases as time passes */}
                              <circle 
                                className="text-blue-600" 
                                strokeWidth="8" 
                                stroke="currentColor" 
                                fill="transparent" 
                                r="40" 
                                cx="50" 
                                cy="50" 
                                strokeLinecap="round"
                                strokeDasharray="251.2"
                                strokeDashoffset={251.2 * (1 - (jobStatus.progress / 100))}
                                transform="rotate(-90 50 50)"
                              />
                            </svg>
                            <div className="absolute inset-0 flex items-center justify-center">
                              <span className="text-xs font-bold">{formatTime(jobStatus.estimated_time_remaining)}</span>
                            </div>
                          </div>
                        </div>
                        <p className="text-sm text-gray-700 font-medium">
                          Estimated time remaining
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          This is an estimate and may vary based on system performance
                        </p>
                      </div>
                    )}
                    
                    {jobStatus.error && (
                      <div className="mt-4 p-3 bg-red-100 text-red-800 rounded-md">
                        <p className="text-sm font-medium">Error: {jobStatus.error}</p>
                      </div>
                    )}
                  </div>
                )}

                {jobStatus?.result && (
                  <div className="mt-6 space-y-4">
                    <h3 className="text-lg font-semibold">Generated Content</h3>
                    
                    {/* Video Preview */}
                    <div>
                      <h3 className="font-medium mb-2">Your Video:</h3>
                      <video 
                        controls 
                        className="w-full rounded-lg border border-gray-200"
                        src={`http://localhost:8000/api/download/${jobStatus.result.video_path}`}
                      ></video>
                      
                      <div className="mt-4">
                        <a 
                          href={`http://localhost:8000/api/download/${jobStatus.result.video_path}`}
                          download
                          className="bg-green-600 text-white px-4 py-2 rounded-lg inline-block"
                        >
                          Download Video
                        </a>
                      </div>
                    </div>
                    
                    {/* Generated Content section */}
                    <div>
                      <h3 className="font-medium mb-2">Generated Script:</h3>
                      <div className="bg-gray-50 p-4 rounded-lg mb-6">
                        <p>{typeof jobStatus.result.script === 'object' ? JSON.stringify(jobStatus.result.script) : jobStatus.result.script}</p>
                      </div>
                      
                      <h3 className="font-medium mb-2">Suggested Effects:</h3>
                      <div className="flex flex-wrap gap-2 mb-6">
                        {jobStatus.result.effects && jobStatus.result.effects.map((effect, index) => (
                          <span key={index} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm">
                            {effect}
                          </span>
                        ))}
                      </div>
                      
                      {/* Show information about custom model and voice if used */}
                      {(jobStatus.result.used_custom_model || jobStatus.result.used_custom_voice) && (
                        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                          {jobStatus.result.used_custom_model && (
                            <p className="text-blue-700 mb-1">✓ Used your custom trained model for personalization</p>
                          )}
                          {jobStatus.result.used_custom_voice && (
                            <p className="text-blue-700">✓ Used your custom voice for narration</p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
} 