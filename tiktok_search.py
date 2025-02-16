import logging
import os
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from transcribing_utils import transcribe_audio, is_english_text, save_video_data
import yt_dlp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create downloads directory if it doesn't exist
from utils import get_query_dir, DOWNLOADS_DIR
DOWNLOADS_DIR.mkdir(exist_ok=True)

def sanitize_filename(filename, max_length=50):
    """
    Create a safe filename by removing invalid characters and limiting length.
    
    Args:
        filename (str): Original filename
        max_length (int): Maximum length for the filename
        
    Returns:
        str: Sanitized filename
    """
    # Remove invalid characters
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in filename)
    # Remove multiple consecutive underscores
    safe_name = '_'.join(filter(None, safe_name.split('_')))
    # Limit length while preserving extension if present
    name_parts = safe_name.rsplit('.', 1)
    if len(name_parts) > 1:
        name, ext = name_parts
        return f"{name[:max_length-len(ext)-1]}.{ext}"
    return safe_name[:max_length]

def get_video_dir(video_id, title, query_dir, create=True):
    """
    Get the directory for a specific video's files.
    
    Args:
        video_id (str): TikTok video ID
        title (str): Video title (used for folder name)
        query_dir (Path): Directory for the search query results
        create (bool): Whether to create the directory if it doesn't exist
        
    Returns:
        Path: Path to the video's directory
    """
    safe_title = sanitize_filename(title)
    video_dir = query_dir / f"{safe_title}_{video_id}"
    
    if create:
        video_dir.mkdir(exist_ok=True)
    
    return video_dir

def download_audio(video_url, video_id, title, query_dir):
    """
    Download audio from a TikTok video.
    
    Args:
        video_url (str): TikTok video URL
        video_id (str): TikTok video ID
        title (str): Video title
        query_dir (Path): Directory for the search query results
        
    Returns:
        str: Path to the downloaded audio file or None if file is too large
    """
    video_dir = get_video_dir(video_id, title, query_dir)
    audio_path = video_dir / 'audio.mp3'
    
    if audio_path.exists():
        logger.info(f"Audio already exists for video {video_id}")
        return str(audio_path)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': str(video_dir / 'audio.%(ext)s'),  # Use a simple fixed filename
        'max_filesize': 10000000,  # 10MB limit to prevent huge downloads
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
            # Find the downloaded audio file
            for file in video_dir.glob('*.mp3'):
                # Rename to standard name
                file.rename(audio_path)
                return str(audio_path)
    except Exception as e:
        logger.error(f"Error downloading audio for video {video_id}: {str(e)}")
        return None

"""
Search for TikTok videos using EnsembleData API.

Args:
    query (str): Search query
    max_results (int): Maximum number of results to return (default: 2)
    query_dir (Path): Directory to save video data (default: None)
    
Returns:
    list: List of video information dictionaries
"""
def search_videos(query, max_results=2, query_dir=None):
    # Load environment variables
    load_dotenv(override=True)
    
    # If no query_dir provided, create a default one
    if query_dir is None:
        query_dir = get_query_dir(query)
    
    # Load API key from environment
    api_key = os.getenv('ENSEMBLEDDATA_API_KEY')
    if not api_key:
        raise ValueError("ENSEMBLEDDATA_API_KEY not found in environment variables")
    
    # EnsembleData API configuration
    root = "https://ensembledata.com/apis"
    endpoint = "/tt/keyword/search"

    review_query = f"{query} review"

    params = {
        "name": review_query,
        "cursor": 0,
        "period": "1",  # Last 24 hours
        "sorting": "0",  # Sort by relevance
        "country": "us",
        "match_exactly": False,
        "get_author_stats": False,
        "token": api_key
    }
    
    videos = []
    try:
        # Search for videos using EnsembleData API
        print(f"Searching TikTok for: {query}")
        print(f"Using URL: {root + endpoint}")
        print(f"With params: {params}")
        
        response = requests.get(root + endpoint, params=params)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response text: {response.text[:500]}...")
        
        response.raise_for_status()
        search_results = response.json()
        
        # The API returns a nested data structure
        if isinstance(search_results, dict) and 'data' in search_results:
            if isinstance(search_results['data'], dict) and 'data' in search_results['data']:
                video_list = search_results['data']['data']
            else:
                video_list = []
        
        print(f"Found {len(video_list)} videos")
            
        for item in video_list[:max_results]:
            # Parse the item data
            try:
                aweme_info = item.get('aweme_info', {})
                author_info = aweme_info.get('author', {})
                video_info = {
                    'video_id': str(aweme_info.get('aweme_id', '')),
                    'title': str(aweme_info.get('desc', '')),
                    'channel': str(author_info.get('nickname', 'TikTok Creator')),
                    'video_url': f"https://www.tiktok.com/@{author_info.get('unique_id', '')}/video/{aweme_info.get('aweme_id', '')}",
                    'duration': int(aweme_info.get('duration', 0)),
                    'view_count': int(aweme_info.get('statistics', {}).get('play_count', 0)),
                    'platform': 'tiktok',
                    'caption': str(aweme_info.get('desc', ''))
                }
            except (KeyError, TypeError, ValueError) as e:
                logger.error(f"Error parsing video data: {str(e)}")
                continue
            
            print(f"\nProcessing video: {video_info['title']}")
            
            # Download audio and get transcript
            audio_path = download_audio(
                    video_info['video_url'],
                    video_info['video_id'],
                    video_info['title'],
                    query_dir
                )
                
            if audio_path:
                # Get transcript
                result = transcribe_audio(audio_path)
                if not result['available']:
                    logger.error(f"Transcription failed: {result['error']}")
                    continue
                    
                transcript = result['transcript']
                logger.info(f"Got transcript: {transcript[:200]}...")
                
                is_english = is_english_text(transcript)
                logger.info(f"Transcript is English: {is_english}")
                
                if transcript and is_english:
                    video_info['transcript'] = transcript
                    videos.append(video_info)
                    
                    # Save video data
                    video_dir = get_video_dir(
                        video_info['video_id'],
                        video_info['title'],
                        query_dir
                    )
                    save_video_data(video_dir, video_info, transcript)
    
    except Exception as e:
        logger.error(f"Error searching TikTok videos: {str(e)}")
    
    return videos

def main():
    """
    Test the TikTok search functionality
    """
    print("Starting TikTok video search...")
    query = "ninja creami"
    print(f"Searching for: {query}")
    
    try:
        videos = search_videos(query, max_results=20)
        
        print(f"\nFound {len(videos)} videos:")
        for video in videos:
            print(f"\nVideo: {video['title']}")
            print(f"Channel: {video['channel']}")
            print(f"URL: {video['video_url']}")
            if 'transcript' in video:
                print(f"Transcript: {video['transcript'][:200]}...")
            else:
                print("Transcript: Not available")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
