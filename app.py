from flask import Flask, render_template, request, jsonify
from youtube_search import search_videos, download_audio, get_video_dir, save_video_data
from transcribing_utils import transcribe_audio
from review_generator import process_query_directory
from reviews import get_product_reviews
from pathlib import Path
import logging
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('product')
    if not query:
        logger.warning('No product query provided')
        error_response = {'error': 'No product query provided'}
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(error_response)
        return render_template('results.html', query='', results=error_response)
    
    try:
        # Get product reviews from existing sources
        logger.info(f'Searching for product: {query}')
        results = get_product_reviews(query)
        
        # Process image URLs
        if results.get('img_urls'):
            logger.info(f'Found {len(results["img_urls"])} images')
            valid_urls = [url for url in results['img_urls'] if url.startswith(('http://', 'https://'))] 
            results['img_urls'] = valid_urls
            logger.info(f'Found {len(valid_urls)} valid images')
        
        # Create timestamp for query directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        query_dir = Path('downloads') / f'{query}-{timestamp}'
        query_dir.mkdir(parents=True, exist_ok=True)
        
        # Start the YouTube search process
        videos = search_videos(query, max_results=2)
        youtube_reviews = []
        
        if videos:
            # Process each video
            for video in videos:
                try:
                    logger.info(f'Processing video: {video["title"]} (ID: {video["video_id"]})')
                    # Download audio and transcribe with Whisper
                    audio_path = download_audio(video['video_url'], video['video_id'], video['title'], query_dir)
                    logger.info(f'Audio download result: {"Success" if audio_path else "Failed"}')
                    
                    if audio_path:
                        logger.info(f'Audio downloaded successfully: {audio_path}')
                        whisper_result = transcribe_audio(audio_path)
                        
                        if whisper_result['available']:
                            logger.info('Whisper transcription successful')
                            
                            # Save video data
                            video_dir = get_video_dir(video['video_id'], video['title'], query_dir)
                            save_video_data(
                                video_dir=video_dir,
                                video_info={
                                    'title': video['title'],
                                    'description': video.get('description', ''),
                                    'channel': video['channel'],
                                    'publishedAt': video.get('published_at', ''),
                                    'platform': 'YouTube',
                                    'statistics': {
                                        'viewCount': str(video.get('view_count', 0)),
                                        'likeCount': str(video.get('like_count', 0)),
                                        'commentCount': str(video.get('comment_count', 0))
                                    },
                                    'video_url': video.get('video_url', ''),
                                },
                                transcript=whisper_result['transcript']
                            )
                            
                            # Generate reviews
                            logger.info('Generating reviews from transcript...')
                            generated_reviews = process_query_directory(str(query_dir))
                            if generated_reviews:
                                logger.info(f'Generated {len(generated_reviews)} reviews')
                                youtube_reviews.extend(generated_reviews)
                            else:
                                logger.warning('No reviews were generated from the transcript')
                                
                except Exception as e:
                    logger.error(f'Error processing video {video["video_id"]}: {str(e)}')
                    continue
        
        # Deduplicate YouTube reviews based on video URL
        if youtube_reviews:
            seen_urls = set()
            unique_reviews = []
            for review in youtube_reviews:
                if review['video_url'] not in seen_urls:
                    seen_urls.add(review['video_url'])
                    unique_reviews.append(review)
            results['youtube_reviews'] = unique_reviews
        
        # For AJAX requests, do the processing and return results
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'success',
                'reviews': results.get('youtube_reviews', []),
                'weighted_avg_rating': results.get('weighted_avg_rating', 0),
                'total_reviews': results.get('total_reviews', 0)
            })
            
        # For direct browser requests, just render the template with any existing results
        # This prevents reprocessing when redirected from search
        return render_template('results.html', query=query, results=results)
                              
    except Exception as e:
        logger.error(f'Error processing request: {str(e)}', exc_info=True)
        error_msg = f'Error processing request: {str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': error_msg})
        return render_template('results.html', query=query, results={'error': error_msg})

if __name__ == '__main__':
    app.run(debug=True)
