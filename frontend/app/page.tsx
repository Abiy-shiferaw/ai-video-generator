'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion } from 'framer-motion';
import axios from 'axios';
import { FaUpload, FaVideo, FaVolumeUp, FaSpinner, FaCheck, FaMicrophone, FaStop, FaImages, FaTrash, FaBullhorn, FaPalette, FaBriefcase, FaLightbulb, FaUserTie, FaBox, FaInfoCircle, FaClock } from 'react-icons/fa';

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
  message?: string;
  error?: string;
  filename: string;
  filepath: string;
  voice_id?: string;
  url?: string;
}

interface CloneVoiceResponse {
  success: boolean;
  message?: string;
  error?: string;
  voice_id: string;
  voice_name: string;
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

// Add a new interface for voice data
interface Voice {
  voice_id: string;
  name: string;
  category: string;
  gender: string;
}

interface VoicesResponse {
  success: boolean;
  voices: Voice[];
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
  const [isAdvancedVideoMode, setIsAdvancedVideoMode] = useState(false);
  const [advancedVideoPrompt, setAdvancedVideoPrompt] = useState('');
  const [advancedVideoStyle, setAdvancedVideoStyle] = useState('realistic');
  const [advancedVideoDuration, setAdvancedVideoDuration] = useState(10);
  const [availableVoices, setAvailableVoices] = useState<Voice[]>([]);
  const [advancedVideoSource, setAdvancedVideoSource] = useState<string | null>(null);
  const [advancedVideoAddVoiceover, setAdvancedVideoAddVoiceover] = useState(false);
  const [advancedVideoVoiceId, setAdvancedVideoVoiceId] = useState<string | null>(null);
  const [showPromptsModal, setShowPromptsModal] = useState(false);
  const [testimonialTemplate, setTestimonialTemplate] = useState('');
  const [productTemplate, setProductTemplate] = useState('');
  const [explainerTemplate, setExplainerTemplate] = useState('');
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Add a new state for the main selected mode
  const [selectedTab, setSelectedTab] = useState<'adCreator' | 'advancedVideo' | 'voice' | null>(null);

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
    
    // Get available effects
    fetchEffects();
    
    // Get available templates
    fetchTemplates();
    
    // Get available voices
    fetchVoices();
    
    // Initialize template prompts
    setTestimonialTemplate(
      "HVAC Testimonial Video with Professional Technician\n\n" +
      "Scene 1: Close-up of an HVAC technician in a branded uniform standing in front of an air conditioning unit at a residential property. The technician should look experienced and trustworthy, talking directly to the camera about our 24/7 emergency services.\n\n" + 
      "Scene 2: Show the technician working on an HVAC system, demonstrating expertise and attention to detail.\n\n" +
      "Scene 3: Technician back on camera explaining how our team guarantees customer satisfaction and showing before/after results."
    );
    
    setProductTemplate(
      "Professional HVAC Product Showcase Video\n\n" +
      "Scene 1: Introduction showing our latest high-efficiency air conditioning unit with clean, modern design and Energy Star rating.\n\n" + 
      "Scene 2: Detailed view of the key features including smart thermostat integration, quiet operation (only 56 decibels), and humidity control system.\n\n" +
      "Scene 3: Demonstration of easy installation process and maintenance, emphasizing the 10-year warranty and 24/7 support."
    );
    
    setExplainerTemplate(
      "HVAC Educational Explainer Video\n\n" +
      "Scene 1: Introduction explaining how heating and cooling systems work in modern homes, with simple diagrams or animations.\n\n" + 
      "Scene 2: Common issues homeowners face with their HVAC systems and warning signs to watch for (unusual noises, inconsistent temperatures, high energy bills).\n\n" +
      "Scene 3: Expert tips for maintaining your HVAC system, including regular filter changes, keeping outdoor units clear, and the importance of professional seasonal tune-ups."
    );
  }, []);

  // Add fetchEffects function
  const fetchEffects = async () => {
    try {
      const response = await axios.get<{effects: Effect[]}>('http://localhost:8000/api/effects');
      // You can store the effects in state if needed
      console.log('Available effects:', response.data);
    } catch (error) {
      console.error('Error fetching effects:', error);
    }
  };

  // Add fetchVoices function
  const fetchVoices = async () => {
    try {
      const response = await axios.get<VoicesResponse>('http://localhost:8000/api/voices/available');
      if (response.data.success && response.data.voices) {
        setAvailableVoices(response.data.voices);
        
        // Default to a professional male voice if available
        const defaultVoice = response.data.voices.find((voice: Voice) => 
          voice.category === 'professional' && voice.gender === 'male'
        );
        
        if (defaultVoice) {
          setAdvancedVideoVoiceId(defaultVoice.voice_id);
        } else if (response.data.voices.length > 0) {
          setAdvancedVideoVoiceId(response.data.voices[0].voice_id);
        }
      }
    } catch (error) {
      console.error('Error fetching voices:', error);
    }
  };

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
    formData.append('file', blob, `recording_${Date.now()}.wav`);
    
    try {
      const response = await axios.post<VoiceUploadResponse>('http://localhost:8000/api/upload-voice', formData);
      if (response.data.success) {
        // Show a dialog to ask the user if they want to clone this voice
        if (confirm('Voice uploaded successfully! Would you like to clone this voice for high-quality AI narration?')) {
          await cloneVoice(response.data.filepath);
        } else {
          // Just use the uploaded voice directly without cloning
          const newVoice: VoiceFile = {
            id: response.data.voice_id || `custom-${Date.now()}`,
            name: response.data.filename,
            url: response.data.url || `/api/voices/${response.data.filename}`
          };
          setUploadedVoices(prev => [...prev, newVoice]);
          if (newVoice.id) {
            setSelectedVoice(newVoice.id);
          }
        }
      }
    } catch (error) {
      console.error('Error uploading voice recording:', error);
      alert('Failed to upload voice recording. Please try again.');
    }
  };
  
  const cloneVoice = async (voiceSamplePath: string) => {
    try {
      // Show a loading state
      setLoading(true);
      setError(null);
      
      // Prompt for a name for the cloned voice
      const voiceName = prompt('Enter a name for your cloned voice:', 'My Custom Voice');
      
      if (!voiceName) {
        setLoading(false);
        return; // User cancelled
      }
      
      // Call the clone voice API
      const response = await axios.post<CloneVoiceResponse>('http://localhost:8000/api/clone-voice', {
        voice_sample_path: voiceSamplePath,
        voice_name: voiceName,
        description: `Cloned voice for ${voiceName}`
      });
      
      if (response.data.success) {
        alert(`Voice "${voiceName}" cloned successfully! You can now use it for video narration.`);
        
        // Refresh the available voices to include the new cloned voice
        fetchVoices();
        
        // Auto-select the new voice
        setSelectedVoice(response.data.voice_id);
      } else {
        alert(`Failed to clone voice: ${response.data.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error cloning voice:', error);
      alert('Failed to clone voice. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  const handleVoiceUpload = async (files: File[]) => {
    if (files.length === 0) return;
    
    const formData = new FormData();
    formData.append('voice', files[0]);
    
    try {
      const response = await axios.post<VoiceUploadResponse>('http://localhost:8000/api/upload-voice', formData);
      if (response.data.success) {
        const newVoice: VoiceFile = {
          id: response.data.voice_id || `custom-${Date.now()}`,
          name: response.data.filename,
          url: response.data.url || `/api/voices/${response.data.filename}`
        };
        setUploadedVoices(prev => [...prev, newVoice]);
        if (newVoice.id) {
          setSelectedVoice(newVoice.id);
        }
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

  // Add this new function
  const handleAdvancedVideoGeneration = async () => {
    if (!advancedVideoPrompt) {
      setError('Please enter a description for your advanced video');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // Define the response type for consistency
      interface AdvancedVideoResponse {
        success: boolean;
        job_id: string;
        message: string;
      }
      
      // Send request to generate advanced video
      const response = await axios.post<AdvancedVideoResponse>('http://localhost:8000/api/generate-advanced-video', {
        prompt: advancedVideoPrompt,
        style: advancedVideoStyle,
        duration: advancedVideoDuration,
        video_source: advancedVideoSource,
        add_voiceover: advancedVideoAddVoiceover,
        voice_id: advancedVideoVoiceId
      });
      
      // Check if the response was successful and has a job_id
      if (response.data.success && response.data.job_id) {
        // Get the job ID and start checking status
        setJobId(response.data.job_id);
        setJobStatus({
          status: 'initializing',
          progress: 0
        });
        
        // Start polling for job status
        const checkStatus = async () => {
          try {
            const statusResponse = await axios.get<JobStatus>(`http://localhost:8000/api/status/${response.data.job_id}`);
            setJobStatus(statusResponse.data);
            
            if (statusResponse.data.status === 'completed' || statusResponse.data.status === 'failed') {
              setLoading(false);
              if (statusResponse.data.status === 'failed') {
                setError(statusResponse.data.error || 'Failed to generate video');
              }
            } else {
              // Continue checking every 2 seconds
              setTimeout(checkStatus, 2000);
            }
          } catch (err) {
            console.error('Error checking job status:', err);
            setLoading(false);
            setError('Failed to check video generation status');
          }
        };
        
        // Start checking immediately
        checkStatus();
        
      } else {
        setError('Failed to generate advanced video');
        setLoading(false);
      }
    } catch (error) {
      console.error('Error generating advanced video:', error);
      setError('Error generating advanced video. Please try again.');
      setLoading(false);
    }
  };

  // Add these new functions
  const handleGenerateAd = async () => {
    if (!brandName || !adText) {
      setError('Please provide a brand name and ad text');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Prepare the request data
      const requestData = {
        ad_text: adText, // Use ad_text to match the backend's expected parameter
        brand_name: brandName,
        tagline: tagline,
        target_audience: targetAudience,
        template: adTemplate,
        style: adStyle,
        color_scheme: colorScheme,
        animation_style: animationStyle,
        duration: adDuration,
        add_voiceover: addVoiceover,
        voice_id: selectedVoice
      };

      // Send request to generate ad
      const response = await axios.post<VideoResponse>(
        'http://localhost:8000/api/generate-ad',
        requestData
      );

      if (response.data.job_id) {
        setJobId(response.data.job_id);
      } else {
        throw new Error('No job ID returned');
      }
    } catch (err) {
      console.error('Error generating ad:', err);
      setLoading(false);
      setError('Failed to generate ad video');
    }
  };

  const handleGenerateAdvancedVideo = async () => {
    if (!advancedVideoPrompt) {
      setError('Please provide a video description');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Prepare the request data
      const requestData = {
        prompt: advancedVideoPrompt,
        style: advancedVideoStyle,
        duration: advancedVideoDuration
      };

      // Send request to generate advanced video
      const response = await axios.post<VideoResponse>(
        'http://localhost:8000/api/generate-advanced-video',
        requestData
      );

      if (response.data.job_id) {
        setJobId(response.data.job_id);
      } else {
        throw new Error('No job ID returned');
      }
    } catch (err) {
      console.error('Error generating advanced video:', err);
      setLoading(false);
      setError('Failed to generate advanced video');
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-900 to-black text-white p-6">
      <div className="max-w-5xl mx-auto">
        <header className="text-center mb-10">
          <h1 className="text-4xl font-bold mb-2 text-gradient bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
            AI Video Generator
          </h1>
          <p className="text-xl text-gray-300">Create professional videos with AI</p>
        </header>

        {!selectedTab ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
            <motion.div 
              className="bg-gradient-to-br from-blue-900/40 to-indigo-900/40 rounded-xl p-6 hover:shadow-xl transition-all border border-blue-800/50 cursor-pointer"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedTab('adCreator')}
            >
              <div className="flex justify-center mb-4">
                <FaBullhorn className="text-5xl text-blue-400" />
              </div>
              <h2 className="text-2xl font-bold text-center mb-2">Professional Ad Creator</h2>
              <p className="text-gray-300 text-center">
                Create sleek, professional-looking animated advertisements with brand customization
              </p>
            </motion.div>

            <motion.div 
              className="bg-gradient-to-br from-purple-900/40 to-pink-900/40 rounded-xl p-6 hover:shadow-xl transition-all border border-purple-800/50 cursor-pointer"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedTab('advancedVideo')}
            >
              <div className="flex justify-center mb-4">
                <FaVideo className="text-5xl text-purple-400" />
              </div>
              <h2 className="text-2xl font-bold text-center mb-2">Advanced Motion Video</h2>
              <p className="text-gray-300 text-center">
                Create dynamic AI-generated videos with real motion and professional effects
              </p>
            </motion.div>

            <motion.div 
              className="bg-gradient-to-br from-green-900/40 to-teal-900/40 rounded-xl p-6 hover:shadow-xl transition-all border border-green-800/50 cursor-pointer"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedTab('voice')}
            >
              <div className="flex justify-center mb-4">
                <FaVolumeUp className="text-5xl text-green-400" />
              </div>
              <h2 className="text-2xl font-bold text-center mb-2">AI Voiceover</h2>
              <p className="text-gray-300 text-center">
                Add professional AI-generated voiceovers to your videos with voice customization
              </p>
            </motion.div>
          </div>
        ) : (
          <motion.button
            className="mb-8 flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
            onClick={() => {
              setSelectedTab(null);
              setPhoto(null);
              setPreview(null);
              setJobId(null);
              setJobStatus(null);
              setError(null);
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Main Menu
          </motion.button>
        )}

        {selectedTab === 'adCreator' && (
          <motion.div 
            className="bg-gradient-to-br from-blue-900/30 to-indigo-900/30 rounded-xl p-8 border border-blue-800/50"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
              <FaBullhorn className="text-blue-400" />
              Professional Ad Creator
            </h2>
            
            {/* Ad Creator Form */}
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-1">Brand Name</label>
                <input
                  type="text"
                  value={brandName}
                  onChange={(e) => setBrandName(e.target.value)}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                  placeholder="Your company name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Ad Text/Script</label>
                <textarea
                  value={adText}
                  onChange={(e) => setAdText(e.target.value)}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white h-32"
                  placeholder="Describe your product or service"
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Tagline</label>
                  <input
                    type="text"
                    value={tagline}
                    onChange={(e) => setTagline(e.target.value)}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                    placeholder="Your catchy tagline"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Target Audience</label>
                  <input
                    type="text"
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                    placeholder="Who is this ad for?"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Ad Template</label>
                  <select
                    value={adTemplate}
                    onChange={(e) => setAdTemplate(e.target.value)}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                  >
                    <option value="product">Product Showcase</option>
                    <option value="testimonial">Testimonial</option>
                    <option value="explainer">Explainer</option>
                    <option value="corporate">Corporate</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Animation Style</label>
                  <select
                    value={animationStyle}
                    onChange={(e) => setAnimationStyle(e.target.value)}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                  >
                    <option value="sleek">Sleek & Smooth</option>
                    <option value="motion_graphics">Motion Graphics</option>
                    <option value="isometric">Isometric</option>
                    <option value="infographic">Animated Infographics</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Color Scheme</label>
                  <select
                    value={colorScheme}
                    onChange={(e) => setColorScheme(e.target.value)}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                  >
                    <option value="blue">Professional Blue</option>
                    <option value="green">Natural Green</option>
                    <option value="purple">Creative Purple</option>
                    <option value="red">Bold Red</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="addVoiceover"
                  checked={addVoiceover}
                  onChange={(e) => setAddVoiceover(e.target.checked)}
                  className="w-4 h-4 bg-gray-800 rounded border-gray-700"
                />
                <label htmlFor="addVoiceover" className="text-sm">Add AI Voiceover</label>
              </div>
              
              {addVoiceover && (
                <div>
                  <label className="block text-sm font-medium mb-1">Voice Style</label>
                  <select
                    value={selectedVoice || ""}
                    onChange={(e) => setSelectedVoice(e.target.value || null)}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                  >
                    <option value="">Select a voice</option>
                    <optgroup label="Professional Voices">
                      {availableVoices
                        .filter(voice => voice.category === 'professional')
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                    <optgroup label="Casual Voices">
                      {availableVoices
                        .filter(voice => voice.category === 'casual')
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                    <optgroup label="Other Voices">
                      {availableVoices
                        .filter(voice => !['professional', 'casual', 'custom'].includes(voice.category))
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                    <optgroup label="Your Custom Voices">
                      {availableVoices
                        .filter(voice => voice.category === 'custom')
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                  </select>
                </div>
              )}
              
              <button
                onClick={() => handleGenerateAd()}
                disabled={loading || !adText || !brandName}
                className={`w-full py-3 px-6 rounded-lg font-medium transition-all ${
                  loading || !adText || !brandName
                    ? 'bg-gray-700 text-gray-400'
                    : 'bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white'
                }`}
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <FaSpinner className="animate-spin mr-2" />
                    Generating Ad...
                  </div>
                ) : (
                  'Generate Professional Ad'
                )}
              </button>
            </div>
          </motion.div>
        )}

        {selectedTab === 'advancedVideo' && (
          <motion.div 
            className="bg-gradient-to-br from-purple-900/30 to-pink-900/30 rounded-xl p-8 border border-purple-800/50"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="p-4 mb-4 bg-white/10 rounded shadow-md">
              <h3 className="text-lg font-medium mb-2 text-white">Video Generation Tips</h3>
              <div className="text-sm text-gray-200">
                <p className="mb-2"><strong>For better AI-generated videos:</strong></p>
                <ul className="list-disc pl-5 mb-3">
                  <li className="mb-1">Select <strong>"Runway"</strong> or <strong>"Stability"</strong> as the video source for true AI generation</li>
                  <li className="mb-1">Be very specific and detailed in your prompts (e.g., "A cinematic drone shot of a coastal city at sunset with waves crashing against cliffs")</li>
                  <li className="mb-1">Include style keywords like "cinematic", "photorealistic", "high-quality", "professional"</li>
                  <li className="mb-1">Mention camera angles: "aerial view", "close-up", "wide angle", "tracking shot"</li>
                  <li className="mb-1">Specify lighting: "golden hour", "dramatic lighting", "soft natural light"</li>
                  <li className="mb-1">For best results, keep scenes simple and focused on 1-2 main elements</li>
                </ul>
              </div>
            </div>
            
            <h2 className="text-2xl font-bold mb-6 text-white">Advanced Video Generation</h2>
            
            {/* Advanced Video Form */}
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-1">Video Description</label>
                <textarea
                  value={advancedVideoPrompt}
                  onChange={(e) => setAdvancedVideoPrompt(e.target.value)}
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white h-32"
                  placeholder="Describe the video you want to create in detail. For best results with hybrid videos, include intro, middle content, and conclusion sections."
                />
                <div className="mt-2">
                  <div className="flex flex-wrap gap-2 mt-1">
                    <button
                      type="button"
                      onClick={() => setShowPromptsModal(true)}
                      className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium rounded text-purple-300 bg-purple-900/40 hover:bg-purple-900/70 transition"
                    >
                      <FaLightbulb className="mr-1" /> Prompt Ideas
                    </button>
                    <button
                      type="button"
                      onClick={() => setAdvancedVideoPrompt(testimonialTemplate)}
                      className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium rounded text-green-300 bg-green-900/40 hover:bg-green-900/70 transition"
                    >
                      <FaUserTie className="mr-1" /> Testimonial
                    </button>
                    <button
                      type="button"
                      onClick={() => setAdvancedVideoPrompt(productTemplate)}
                      className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium rounded text-blue-300 bg-blue-900/40 hover:bg-blue-900/70 transition"
                    >
                      <FaBox className="mr-1" /> Product Demo
                    </button>
                    <button
                      type="button"
                      onClick={() => setAdvancedVideoPrompt(explainerTemplate)}
                      className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium rounded text-amber-300 bg-amber-900/40 hover:bg-amber-900/70 transition"
                    >
                      <FaInfoCircle className="mr-1" /> Explainer
                    </button>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Video Source</label>
                  <select
                    value={advancedVideoSource || ""}
                    onChange={(e) => setAdvancedVideoSource(e.target.value || null)}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                  >
                    <option value="">Auto (based on style)</option>
                    <option value="hybrid">Hybrid (AI + Stock Video)</option>
                    <option value="runway">AI Motion (RunwayML)</option>
                    <option value="stability">AI Diffusion (Stability)</option>
                    <option value="pexels">Stock Video (Pexels)</option>
                  </select>
                </div>
              
                <div>
                  <label className="block text-sm font-medium mb-1">Video Style</label>
                  <select
                    value={advancedVideoStyle}
                    onChange={(e) => setAdvancedVideoStyle(e.target.value)}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                  >
                    <option value="realistic">Realistic</option>
                    <option value="animated">Animated</option>
                    <option value="creative">Creative</option>
                    <option value="cinematic">Cinematic</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Duration (seconds)</label>
                  <input
                    type="number"
                    min="3"
                    max="60"
                    value={advancedVideoDuration}
                    onChange={(e) => setAdvancedVideoDuration(parseInt(e.target.value, 10))}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                  />
                </div>
                
                <div className="flex flex-col justify-end">
                  <div className="flex items-center space-x-2 pb-2 pt-6">
                    <input
                      type="checkbox"
                      id="add-voiceover-advanced"
                      checked={advancedVideoAddVoiceover}
                      onChange={(e) => setAdvancedVideoAddVoiceover(e.target.checked)}
                      className="w-4 h-4 bg-gray-800 rounded border-gray-700"
                    />
                    <label htmlFor="add-voiceover-advanced" className="text-sm">Add AI Voiceover</label>
                  </div>
                </div>
              </div>
              
              {advancedVideoAddVoiceover && (
                <div>
                  <label className="block text-sm font-medium mb-1">Voice</label>
                  <select
                    value={advancedVideoVoiceId || ""}
                    onChange={(e) => setAdvancedVideoVoiceId(e.target.value || null)}
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                  >
                    <option value="">Default Voice</option>
                    <optgroup label="Professional Voices">
                      {availableVoices
                        .filter(voice => voice.category === 'professional')
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                    <optgroup label="Casual Voices">
                      {availableVoices
                        .filter(voice => voice.category === 'casual')
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                    <optgroup label="Other Voices">
                      {availableVoices
                        .filter(voice => !['professional', 'casual', 'custom'].includes(voice.category))
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                    <optgroup label="Your Custom Voices">
                      {availableVoices
                        .filter(voice => voice.category === 'custom')
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                  </select>
                </div>
              )}
              
              <button
                onClick={handleAdvancedVideoGeneration}
                disabled={loading || !advancedVideoPrompt}
                className={`w-full py-3 px-6 rounded-lg font-medium transition-all ${
                  loading || !advancedVideoPrompt
                    ? 'bg-gray-700 text-gray-400'
                    : 'bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white'
                }`}
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <FaSpinner className="animate-spin mr-2" />
                    Generating Video...
                  </div>
                ) : advancedVideoSource === 'hybrid' ? (
                  'Generate Hybrid Video'
                ) : (
                  'Generate Advanced Video'
                )}
              </button>
            </div>
          </motion.div>
        )}

        {selectedTab === 'voice' && (
          <motion.div 
            className="bg-gradient-to-br from-green-900/30 to-teal-900/30 rounded-xl p-8 border border-green-800/50"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
              <FaVolumeUp className="text-green-400" />
              AI Voiceover
            </h2>
            
            {/* Voice Generation Form */}
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-1">Script Text</label>
                <textarea
                  className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white h-32"
                  placeholder="Enter the text you want to convert to voice"
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Voice Style</label>
                  <select
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                    value={selectedVoice || ""}
                    onChange={(e) => setSelectedVoice(e.target.value || null)}
                  >
                    <option value="">Select a voice</option>
                    <optgroup label="Professional Voices">
                      {availableVoices
                        .filter(voice => voice.category === 'professional')
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                    <optgroup label="Casual Voices">
                      {availableVoices
                        .filter(voice => voice.category === 'casual')
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                    <optgroup label="Other Voices">
                      {availableVoices
                        .filter(voice => !['professional', 'casual', 'custom'].includes(voice.category))
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                    <optgroup label="Your Custom Voices">
                      {availableVoices
                        .filter(voice => voice.category === 'custom')
                        .map(voice => (
                          <option key={voice.voice_id} value={voice.voice_id}>
                            {voice.name}
                          </option>
                        ))
                      }
                    </optgroup>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium mb-1">Speech Pace</label>
                  <select
                    className="w-full bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-white"
                  >
                    <option value="slow">Slow</option>
                    <option value="medium" selected>Medium</option>
                    <option value="fast">Fast</option>
                  </select>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-1">Upload Custom Voice (Optional)</label>
                <div className="border-dashed border-2 border-gray-600 rounded-lg p-4 text-center">
                  <div className="flex items-center justify-center mb-2">
                    <FaMicrophone className="text-gray-400 text-xl" />
                  </div>
                  <p className="text-sm text-gray-400">Drag & drop a voice sample file or click to browse</p>
                </div>
              </div>

              <button
                className="w-full py-3 px-6 rounded-lg font-medium transition-all bg-gradient-to-r from-green-500 to-teal-600 hover:from-green-600 hover:to-teal-700 text-white"
              >
                Generate Voiceover
              </button>
            </div>
          </motion.div>
        )}

        {/* Results Section */}
        {jobStatus?.status === 'completed' && jobStatus?.result && (
          <motion.div 
            className="mt-8 bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-xl p-6 border border-gray-700/50"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
              <FaCheck className="text-green-400" />
              Your Video is Ready!
            </h2>
            
            <div className="aspect-video bg-black rounded-lg overflow-hidden mb-4">
              <video 
                src={`http://localhost:8000/api/download/${jobStatus?.result?.video_path}`}
                controls
                className="w-full h-full"
              />
            </div>
            
            <div className="flex flex-wrap gap-3 mt-4">
              <button
                className="py-2 px-4 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2 transition-colors"
                onClick={() => window.open(`http://localhost:8000/api/download/${jobStatus?.result?.video_path}`, '_blank')}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Video
              </button>
              
              <button
                className="py-2 px-4 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2 transition-colors"
                onClick={() => {
                  setJobId(null);
                  setJobStatus(null);
                }}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Create Another
              </button>
            </div>
          </motion.div>
        )}

        {/* Loading and error states */}
        {loading && !jobStatus && (
          <div className="text-center my-8">
            <FaSpinner className="animate-spin text-4xl mx-auto mb-4 text-blue-500" />
            <p className="text-gray-300">Uploading and processing...</p>
          </div>
        )}
        
        {/* Show progress indicator when job is in progress */}
        {loading && jobStatus && jobStatus.status !== 'completed' && jobStatus.status !== 'failed' && (
          <div className="bg-gray-900/70 border border-gray-700 rounded-lg p-6 my-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-300 capitalize">{jobStatus.status.replace('_', ' ')}</span>
              <span className="text-blue-400 font-semibold">{jobStatus.progress}%</span>
            </div>
            
            {/* Progress bar */}
            <div className="w-full bg-gray-800 rounded-full h-2.5 mb-3">
              <div 
                className="bg-gradient-to-r from-blue-500 to-purple-600 h-2.5 rounded-full transition-all duration-300 ease-out" 
                style={{ width: `${jobStatus.progress}%` }}
              ></div>
            </div>
            
            {/* Estimated time remaining */}
            {jobStatus?.estimated_time_remaining !== null && jobStatus?.estimated_time_remaining !== undefined && jobStatus?.estimated_time_remaining > 0 && (
              <div className="text-sm text-gray-400 flex items-center">
                <FaClock className="mr-2" />
                <span>
                  Estimated time remaining: {
                    jobStatus.estimated_time_remaining > 60 
                      ? `${Math.ceil(jobStatus.estimated_time_remaining / 60)} minutes` 
                      : `${jobStatus.estimated_time_remaining} seconds`
                  }
                </span>
              </div>
            )}
            
            {/* Status description */}
            <div className="mt-3 text-sm text-gray-300">
              {jobStatus.status === 'generating_script' && (
                <p>Creating an engaging script based on your input...</p>
              )}
              {jobStatus.status === 'generating_video' && (
                <p>Crafting your video with AI-powered visuals...</p>
              )}
              {jobStatus.status === 'adding_voiceover' && (
                <p>Adding professional narration to your video...</p>
              )}
              {jobStatus.status === 'enhancing_video' && (
                <p>Polishing and enhancing your video for best quality...</p>
              )}
              {jobStatus.status === 'processing_audio' && (
                <p>Fine-tuning audio for perfect synchronization...</p>
              )}
              {jobStatus.status === 'finalizing' && (
                <p>Putting the finishing touches on your masterpiece...</p>
              )}
            </div>
          </div>
        )}
        
        {error && (
          <div className="bg-red-900/30 border border-red-800 rounded-lg p-4 my-6 text-center">
            <p className="text-red-300">{error}</p>
          </div>
        )}

        {/* Prompt Templates Modal */}
        {showPromptsModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80" onClick={() => setShowPromptsModal(false)}>
            <div className="bg-gray-900 border border-gray-700 rounded-lg max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <h3 className="text-xl font-bold mb-4">Smart Prompt Templates</h3>
              <div className="space-y-4">
                <div className="border border-gray-700 rounded-lg p-4">
                  <h4 className="text-lg font-medium text-green-400 mb-2 flex items-center"><FaUserTie className="mr-2" /> HVAC Testimonial Template</h4>
                  <p className="text-gray-300 mb-2 text-sm">Perfect for creating authentic testimonial videos with HVAC professionals.</p>
                  <div className="bg-gray-800 p-3 rounded text-sm">
                    <pre className="whitespace-pre-wrap">{testimonialTemplate}</pre>
                  </div>
                  <button 
                    className="mt-3 bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm transition"
                    onClick={() => {
                      setAdvancedVideoPrompt(testimonialTemplate);
                      setShowPromptsModal(false);
                    }}
                  >
                    Use This Template
                  </button>
                </div>
                
                <div className="border border-gray-700 rounded-lg p-4">
                  <h4 className="text-lg font-medium text-blue-400 mb-2 flex items-center"><FaBox className="mr-2" /> Product Demo Template</h4>
                  <p className="text-gray-300 mb-2 text-sm">Showcase your products with this structured demo format.</p>
                  <div className="bg-gray-800 p-3 rounded text-sm">
                    <pre className="whitespace-pre-wrap">{productTemplate}</pre>
                  </div>
                  <button 
                    className="mt-3 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition"
                    onClick={() => {
                      setAdvancedVideoPrompt(productTemplate);
                      setShowPromptsModal(false);
                    }}
                  >
                    Use This Template
                  </button>
                </div>
                
                <div className="border border-gray-700 rounded-lg p-4">
                  <h4 className="text-lg font-medium text-amber-400 mb-2 flex items-center"><FaInfoCircle className="mr-2" /> Explainer Video Template</h4>
                  <p className="text-gray-300 mb-2 text-sm">Educational content that explains concepts clearly.</p>
                  <div className="bg-gray-800 p-3 rounded text-sm">
                    <pre className="whitespace-pre-wrap">{explainerTemplate}</pre>
                  </div>
                  <button 
                    className="mt-3 bg-amber-600 hover:bg-amber-700 text-white px-3 py-1 rounded text-sm transition"
                    onClick={() => {
                      setAdvancedVideoPrompt(explainerTemplate);
                      setShowPromptsModal(false);
                    }}
                  >
                    Use This Template
                  </button>
                </div>
              </div>
              <div className="mt-5 flex justify-end">
                <button 
                  className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded transition"
                  onClick={() => setShowPromptsModal(false)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
} 