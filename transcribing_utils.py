"""
Utility functions for transcribing audio using OpenAI's Whisper API.
"""

import os
import logging
from pathlib import Path
from openai import OpenAI
from langdetect import detect, DetectorFactory

# Set seed for consistent language detection
DetectorFactory.seed = 0

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_english_text(text):
    """
    Check if the given text is in English.
    
    Args:
        text (str): Text to check
        
    Returns:
        bool: True if text is in English, False otherwise
    """
    try:
        detected_language = detect(text)
        logger.info(f"Detected language: {detected_language}")
        return detected_language == 'en'
    except:
        return False

def transcribe_audio(audio_path):
    """
    Transcribe audio using OpenAI's Whisper API.
    
    Args:
        audio_path (str): Path to the audio file
        
    Returns:
        dict: Dictionary containing transcription info
            {
                'available': bool,
                'transcript': str or None,
                'transcript_path': str or None,
                'error': str or None
            }
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                'available': False,
                'transcript': None,
                'transcript_path': None,
                'error': "OPENAI_API_KEY not found in environment variables"
            }
        
        client = OpenAI()

        logger.info(f"Transcribing audio: {audio_path}")
        
        # Read first 20MB of audio
        MAX_SIZE = 20 * 1024 * 1024  # 20MB in bytes
        logger.info(f"Reading up to {MAX_SIZE/1024/1024:.1f}MB of audio from {audio_path}")
        
        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read(MAX_SIZE)
            
        # Create a temporary file with truncated audio
        temp_audio_path = Path(audio_path).with_suffix('.temp.mp3')
        with open(temp_audio_path, "wb") as temp_file:
            temp_file.write(audio_data)
        
        # Transcribe the truncated audio
        with open(temp_audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
            transcript = str(response) if response else ''
            logger.info(f"Raw transcription response: {transcript[:200]}...")
            
        # Clean up temporary file
        temp_audio_path.unlink()
        
        # Check if transcript is in English
        if not is_english_text(transcript):
            return {
                'available': False,
                'transcript': None,
                'transcript_path': None,
                'error': 'Transcript is not in English'
            }
            
        # Save transcript to file
        transcript_path = Path(audio_path).with_suffix('.txt')
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
        
        return {
            'available': True,
            'transcript': transcript,
            'transcript_path': str(transcript_path),
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Whisper transcription error: {str(e)}", exc_info=True)
        return {
            'available': False,
            'transcript': None,
            'transcript_path': None,
            'error': f"Whisper transcription failed: {str(e)}"
        }

def save_video_data(video_dir, video_info, transcript):
    """
    Save video information and transcript to a JSON file.
    
    Args:
        video_dir (Path): Directory to save the video data
        video_info (dict): Dictionary containing video information
        transcript (str): Video transcript
    """
    import json
    
    try:
        data = {
            'video_info': video_info,
            'transcript': transcript
        }
        
        output_path = video_dir / 'video_data.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"Error saving video data: {str(e)}", exc_info=True)
