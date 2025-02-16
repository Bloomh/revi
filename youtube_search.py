from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
import os
import logging
import yt_dlp
from pathlib import Path
import html
import pickle
from transcribing_utils import transcribe_audio, is_english_text, save_video_data
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth2 configuration
SCOPES = [
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube.readonly'
]
TOKEN_FILE = 'token.pickle'
CREDENTIALS_FILE = 'youtube_client_secrets.json'

# Create downloads directory if it doesn't exist
DOWNLOADS_DIR = Path('downloads')
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Load environment variables
load_dotenv(override=True)

def get_video_details(youtube, video_id):
    """
    Get detailed information about a specific video.
    
    Args:
        youtube: Authenticated YouTube service instance
        video_id (str): YouTube video ID
        
    Returns:
        dict: Video details including statistics and description
    """
    try:
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()
        
        if response['items']:
            video = response['items'][0]
            return {
                'title': video['snippet'].get('title', ''),
                'description': video['snippet'].get('description', ''),
                'channel': video['snippet'].get('channelTitle', ''),
                'publishedAt': video['snippet'].get('publishedAt', ''),
                'statistics': video['statistics'],
                'duration': video['contentDetails'].get('duration', ''),
                'defaultLanguage': video['snippet'].get('defaultLanguage', ''),
                'defaultAudioLanguage': video['snippet'].get('defaultAudioLanguage', '')
            }
        return None
        
    except Exception as e:
        logger.error(f"Error getting video details: {str(e)}")
        return None

def search_videos(query, max_results=1):
    """
    Search for YouTube videos using the YouTube Data API.
    
    Args:
        query (str): Search query
        max_results (int): Maximum number of results to return (default: 5)
        
    Returns:
        list: List of video information dictionaries
    """
    # Get both API keys
    api_key = os.getenv("YOUTUBE_API_KEY")
    api_key_2 = os.getenv("YOUTUBE_API_KEY_2")
    
    for current_key in [api_key, api_key_2]:
        if not current_key:
            continue
            
        logger.info(f"Trying API key: {current_key[-10:]}")
        
        try:
            # Create YouTube API client with cache disabled
            youtube = build('youtube', 'v3', developerKey=current_key, cache_discovery=False, static_discovery=False)

            review_query = f"{query} review"
            
            # Call the search.list method
            search_response = youtube.search().list(
                q=review_query,
                part='id,snippet',
                maxResults=max_results,  # Request more results since we'll filter some out
                type='video',
                relevanceLanguage='en'  # Prefer English results
            ).execute()
            
            videos = []
            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                
                # Get video details including language information
                video_response = youtube.videos().list(
                    part='statistics,contentDetails,snippet',
                    id=video_id
                ).execute()
                
                video_details = video_response['items'][0]
                stats = video_details['statistics']
                duration = video_details['contentDetails']['duration']
                
                # Get video language information
                default_language = video_details['snippet'].get('defaultLanguage')
                default_audio_language = video_details['snippet'].get('defaultAudioLanguage')
                title = item['snippet']['title']
                
                # Check if video title is in English
                is_title_english = is_english_text(title)
                
                # Consider video as English if:
                # 1. Default language is English, or
                # 2. Default audio language is English, or
                # 3. Title is in English (as fallback)
                is_english_video = (
                    (default_language and default_language.startswith('en')) or
                    (default_audio_language and default_audio_language.startswith('en')) or
                    is_title_english
                )
                
                if is_english_video:
                    video_info = {
                        'title': title,
                        'description': item['snippet']['description'],
                        'channel': item['snippet']['channelTitle'],
                        'published_at': item['snippet']['publishedAt'],
                        'thumbnail': item['snippet']['thumbnails']['high']['url'],
                        'video_id': video_id,
                        'video_url': f'https://www.youtube.com/watch?v={video_id}',
                        'view_count': stats.get('viewCount', 0),
                        'like_count': stats.get('likeCount', 0),
                        'comment_count': stats.get('commentCount', 0),
                        'duration': duration,
                        'language': default_language or default_audio_language or ('en' if is_title_english else 'unknown')
                    }
                    videos.append(video_info)
                    
                    # Print video details
                    print(f"\nVideo found:")
                    print(f"Title: {video_info['title']}")
                    print(f"Channel: {video_info['channel']}")
                    print(f"Views: {video_info['view_count']}")
                    print(f"Likes: {video_info['like_count']}")
                    print(f"Language: {video_info['language']}")
                    print(f"URL: {video_info['video_url']}")
                    print("---")
                else:
                    logger.info(f"Skipping non-English video: {title}")
    
        except Exception as e:
            if 'quota' in str(e).lower():
                logger.warning(f"API key quota exceeded, trying next key...")
                continue
            logger.error(f"Error searching videos: {str(e)}", exc_info=True)
            continue
            
        # If we get here, the search was successful
        return videos
    
    # If we get here, all keys failed
    logger.error("All API keys have failed or exceeded quota")
    return []

def get_query_dir(query):
    """
    Get the directory for a specific search query's results.
    
    Args:
        query (str): Search query
        
    Returns:
        Path: Path to the query's directory
    """
    # Clean the query to make it filesystem-friendly
    clean_query = ''.join(c for c in query if c.isalnum() or c in ' -_')[:50].strip()
    # Add timestamp to make each search unique
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    query_dir = DOWNLOADS_DIR / f"{clean_query}-{timestamp}"
    query_dir.mkdir(parents=True, exist_ok=True)
    return query_dir

def get_video_dir(video_id, title, query_dir, create=True):
    """
    Get the directory for a specific video's files.
    
    Args:
        video_id (str): YouTube video ID
        title (str): Video title (used for folder name)
        create (bool): Whether to create the directory if it doesn't exist
        
    Returns:
        Path: Path to the video's directory
    """
    # Clean the title to make it filesystem-friendly
    clean_title = ''.join(c for c in title if c.isalnum() or c in ' -_')[:50].strip()
    video_dir = query_dir / f"{video_id}-{clean_title}"
    
    if create:
        video_dir.mkdir(parents=True, exist_ok=True)
    
    return video_dir

def download_audio(video_url, video_id, title, query_dir):
    """
    Download audio from a YouTube video.
    
    Args:
        video_url (str): YouTube video URL
        video_id (str): YouTube video ID
        title (str): Video title
        query_dir (Path): Directory for the search query results
        
    Returns:
        str: Path to the downloaded audio file or None if file is too large
    """
    try:
        # First check the file size
        info_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            filesize = info.get('filesize') or info.get('filesize_approx', 0)
            filesize_mb = filesize / (1024 * 1024)  # Convert to MB
            
            if filesize_mb > 20:
                logger.warning(f"Skipping download: File size ({filesize_mb:.1f}MB) exceeds 20MB limit")
                return None
        
        video_dir = get_video_dir(video_id, title, query_dir)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(video_dir / 'audio.%(ext)s'),
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Downloading audio from: {video_url}")
            info = ydl.extract_info(video_url, download=True)
            audio_path = video_dir / 'audio.mp3'
            logger.info(f"Audio downloaded to: {audio_path}")
            return str(audio_path)
            
    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        return None

def get_authenticated_service():
    """
    Get an authenticated YouTube service instance using OAuth2.
    """
    creds = None
    
    # Load existing credentials from token.pickle if it exists
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials don't exist or are invalid, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"'{CREDENTIALS_FILE}' not found. Please download it from Google Cloud Console "
                    "and save it in the project directory."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save credentials for future use
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('youtube', 'v3', credentials=creds)

def get_transcript(video_id, title, query_dir):
    """
    Get the transcript of a YouTube video.
    
    Args:
        video_id (str): YouTube video ID
        
    Returns:
        dict: Dictionary containing transcript info or None if not available
            {
                'available': bool,
                'transcript': str or None,
                'transcript_path': str or None,
                'error': str or None
            }
    """
    result = {
        'available': False,
        'transcript': None,
        'transcript_path': None,
        'error': None
    }
    
    try:
        youtube = get_authenticated_service()
        
        # Get caption tracks
        captions_response = youtube.captions().list(
            part='snippet',
            videoId=video_id
        ).execute()
        
        if not captions_response.get('items'):
            result['error'] = "No captions available"
            return result
            
        # Get the first available caption track (usually the automatic captions)
        caption_id = captions_response['items'][0]['id']
        
        try:
            # Try to download the caption track
            caption = youtube.captions().download(
                id=caption_id,
                tfmt='srt'
            ).execute()
            
            # Parse and clean up the transcript
            transcript = ""
            for line in caption.decode('utf-8').split('\n'):
                # Skip timestamp lines and empty lines
                if not line.strip() or '-->' in line or line.strip().isdigit():
                    continue
                # Unescape HTML entities and add to transcript
                transcript += html.unescape(line.strip()) + " "
            
            # Check if transcript is in English
            if not is_english_text(transcript):
                result.update({
                    'available': False,
                    'transcript': None,
                    'transcript_path': None,
                    'error': 'Transcript is not in English'
                })
            else:
                # Save transcript to file
                video_dir = get_video_dir(video_id, title, query_dir)
                transcript_path = video_dir / 'transcript.txt'
                transcript_path.write_text(transcript)
                logger.info(f"Transcript saved to: {transcript_path}")
                
                result.update({
                    'available': True,
                    'transcript': transcript,
                    'transcript_path': str(transcript_path)
                })
            
        except Exception as e:
            if 'insufficient' in str(e) or 'forbidden' in str(e):
                result['error'] = "Transcript not publicly available"
            else:
                result['error'] = str(e)
            
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error accessing captions: {str(e)}")
    
    return result

def main():
    try:
        # Get search query from user
        query = input("Enter search query: ")
        print(f"\nSearching for videos matching: {query}")
        
        # Create a directory for this search query
        query_dir = get_query_dir(query)
        print(f"\nStoring results in: {query_dir}")
        
        # Search for videos
        videos = search_videos(query)
        print(f"\nTotal results: {len(videos)}")
        
        # Process each video
        for video in videos:
            print(f"\nProcessing video: {video['title']}")
            video_id = video['video_id']
            
            # Try to get transcript first
            print("Checking YouTube transcript availability...")
            transcript_result = get_transcript(video_id, video['title'], query_dir)
            
            if transcript_result['available']:
                print("YouTube transcript available! Downloading...")
                print(f"Transcript saved to: {transcript_result['transcript_path']}")
                print(f"Preview (first 200 chars):\n{transcript_result['transcript'][:200]}...")
            else:
                print(f"YouTube transcript not available: {transcript_result['error']}")
                print("Downloading audio for Whisper transcription...")
                
                # Download audio and transcribe with Whisper
                audio_path = download_audio(video['video_url'], video['video_id'], video['title'], query_dir)
                if audio_path is None:
                    print("Skipping transcription: Audio file too large")
                elif audio_path:
                    print(f"Audio downloaded successfully to: {audio_path}")
                    print("Transcribing with Whisper...")
                    whisper_result = transcribe_audio(audio_path)
                    
                    if whisper_result['available']:
                        print("Whisper transcription successful!")
                        print(f"Transcript saved to: {whisper_result['transcript_path']}")
                        print(f"Preview (first 200 chars):\n{whisper_result['transcript'][:200]}...")
                        
                        # Save all video data to JSON
                        video_dir = get_video_dir(video['video_id'], video['title'], query_dir)
                        save_video_data(
                            video_dir=video_dir,
                            video_info={
                                'title': video['title'],
                                'description': video.get('description', ''),
                                'channel': video['channel'],
                                'publishedAt': video.get('published_at', ''),
                                'statistics': {
                                    'viewCount': str(video.get('view_count', 0)),
                                    'likeCount': str(video.get('like_count', 0)),
                                    'commentCount': str(video.get('comment_count', 0))
                                },
                                'duration': video.get('duration', ''),
                                'language': video.get('language', '')
                            },
                            transcript=whisper_result['transcript']
                        )
                        print(f"Video data saved to: {video_dir / 'video_data.json'}")
                    else:
                        print(f"Whisper transcription failed: {whisper_result['error']}")
                else:
                    print("Failed to download audio")
            
            print("---")
    
    except Exception as e:
        logger.error(f"Main error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
