from flask import Flask, render_template, request, jsonify
from youtube_search import search_videos as search_youtube_videos, download_audio as download_youtube_audio, get_video_dir as get_youtube_video_dir, save_video_data
from tiktok_search import search_videos as search_tiktok_videos, download_audio as download_tiktok_audio, get_video_dir as get_tiktok_video_dir
from transcribing_utils import transcribe_audio
from review_generator import process_query_directory
from reviews import get_product_reviews, get_review_summary
import logging
import json
from utils import get_query_dir

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

        summary_result = get_review_summary(query, results)
        if summary_result['error']:
            logger.warning(f'Error getting review summary: {summary_result["error"]}')
        else:
            logger.info('Successfully retrieved review summary')
            logger.info(f'Review summary: {summary_result["summary"]}')
            results['summary'] = summary_result["summary"]
        
        # Create directory for this search query
        query_dir = get_query_dir(query)
        
        # Start the YouTube search process
        youtube_videos = search_youtube_videos(query, max_results=4, query_dir=query_dir)
        youtube_reviews = []
        
        # Start the TikTok search process
        tiktok_videos = search_tiktok_videos(query, max_results=8, query_dir=query_dir)
        tiktok_reviews = []
        
        # Process YouTube videos
        if youtube_videos:
            for video in youtube_videos:
                try:
                    logger.info(f'Processing YouTube video: {video["title"]} (ID: {video["video_id"]})')
                    # Download audio and transcribe with Whisper
                    audio_path = download_youtube_audio(video['video_url'], video['video_id'], video['title'], query_dir)
                    logger.info(f'Audio download result: {"Success" if audio_path else "Failed"}')
                    
                    if audio_path:
                        logger.info(f'Audio downloaded successfully: {audio_path}')
                        whisper_result = transcribe_audio(audio_path)
                        
                        if whisper_result['available']:
                            logger.info('Whisper transcription successful')
                            
                            # Save video data
                            video_dir = get_youtube_video_dir(video['video_id'], video['title'], query_dir)
                            save_video_data(
                                video_dir=video_dir,
                                video_info={
                                    'title': video['title'],
                                    'description': video.get('description', ''),
                                    'channel': video['channel'],
                                    'publishedAt': video.get('published_at', ''),
                                    'platform': 'youtube',
                                    'statistics': {
                                        'viewCount': str(video.get('view_count', 0)),
                                        'likeCount': str(video.get('like_count', 0)),
                                        'commentCount': str(video.get('comment_count', 0))
                                    },
                                    'video_url': video.get('video_url', ''),
                                },
                                transcript=whisper_result['transcript']
                            )
                            
                            youtube_reviews.append({
                                'title': video['title'],
                                'url': video['video_url'],
                                'transcript': whisper_result['transcript'],
                                'platform': 'youtube',
                                'channel': video['channel']
                            })
                except Exception as e:
                    logger.error(f'Error processing YouTube video: {str(e)}')
                    
        # Process TikTok videos
        if tiktok_videos:
            for video in tiktok_videos:
                try:
                    logger.info(f'Processing TikTok video: {video["title"]} (ID: {video["video_id"]})')
                    # Download audio and transcribe with Whisper
                    audio_path = download_tiktok_audio(video['video_url'], video['video_id'], video['title'], query_dir)
                    logger.info(f'Audio download result: {"Success" if audio_path else "Failed"}')
                    
                    if audio_path:
                        logger.info(f'Audio downloaded successfully: {audio_path}')
                        whisper_result = transcribe_audio(audio_path)
                        
                        if whisper_result['available']:
                            logger.info('Whisper transcription successful')
                            
                            # Save video data
                            video_dir = get_tiktok_video_dir(video['video_id'], video['title'], query_dir)
                            save_video_data(
                                video_dir=video_dir,
                                video_info={
                                    'title': video['title'],
                                    'channel': video['channel'],
                                    'platform': 'tiktok',
                                    'description': video.get('caption', ''),
                                    'statistics': {
                                        'viewCount': str(video.get('view_count', 0))
                                    },
                                    'video_url': video.get('video_url', ''),
                                },
                                transcript=whisper_result['transcript']
                            )
                            
                            tiktok_reviews.append({
                                'title': video['title'],
                                'url': video['video_url'],
                                'transcript': whisper_result['transcript'],
                                'platform': 'tiktok',
                                'channel': video['channel']
                            })
                except Exception as e:
                    logger.error(f'Error processing TikTok video: {str(e)}')
                    
        # Generate reviews from all videos
        all_reviews = youtube_reviews + tiktok_reviews
        if all_reviews:
            logger.info('Generating reviews from transcripts...')
            generated_reviews = process_query_directory(str(query_dir))
            if generated_reviews:
                logger.info(f'Generated {len(generated_reviews)} reviews')
                results['reviews'] = generated_reviews
            else:
                logger.warning('No reviews were generated from the transcript')
                results['reviews'] = all_reviews
                
    except Exception as e:
        logger.error(f'Error processing search: {str(e)}')
        error_msg = f'Error processing search: {str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': error_msg})
        return render_template('results.html', query=query, results={'error': error_msg})

    # For AJAX requests, return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'status': 'success', 
            'reviews': results.get('reviews', []),
            'weighted_avg_rating': results.get('weighted_avg_rating', 0),
            'total_reviews': results.get('total_reviews', 0),
            'summary': results.get('summary'),
            'img_urls': results.get('img_urls', [])
        })
    
    # For direct browser requests, render the template
    return render_template('results.html', query=query, results=results)

if __name__ == '__main__':
    app.run(debug=True)
