from flask import Flask, render_template, request, jsonify
from reviews import get_product_reviews
import logging

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
        return render_template('results.html',
                             query='',
                             results={'error': 'No product query provided'})
    
    try:
        logger.info(f'Searching for product: {query}')
        results = get_product_reviews(query)
        
        # Log image URLs
        if results.get('img_urls'):
            logger.info(f'Found {len(results["img_urls"])} images:')
            valid_urls = []
            for i, url in enumerate(results['img_urls']):
                logger.info(f'Image {i+1}: {url}')
                if url.startswith(('http://', 'https://')):
                    valid_urls.append(url)
                else:
                    logger.warning(f'Invalid image URL format: {url}')
            results['img_urls'] = valid_urls
            logger.info(f'Found {len(valid_urls)} valid images')
        else:
            logger.info('No images found in results')
        
        return render_template('results.html',
                              query=query,
                              results=results)
    except Exception as e:
        logger.error(f'Error processing request: {str(e)}', exc_info=True)
        return render_template('results.html',
                              query=query,
                              results={'error': f'Error processing request: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)
