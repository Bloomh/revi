import requests
from typing import Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()

def get_product_reviews(query: str, pages: int = 2) -> Dict[str, Any]:
    """
    Fetch and analyze product reviews from Google Shopping.
    
    Args:
        query (str): The product search query
        pages (int): Number of pages to scrape (default: 2)
    
    Returns:
        Dict containing:
        - total_reviews: Total number of reviews
        - weighted_avg_rating: Average rating weighted by review count
        - img_urls: List of URLs of product images
        - error: Error message if any
    """
    try:
        payload = {
            'source': 'google_shopping_search',
            'domain': 'com',
            'query': query,
            'pages': pages,
            'parse': True,
            'context': [
                {'key': 'sort_by', 'value': 'r'},
            ],
        }

        response = requests.request(
            'POST',
            'https://realtime.oxylabs.io/v1/queries',
            auth=(os.getenv('OXYLABS_USER'), os.getenv('OXYLABS_PASS')),
            json=payload,
            timeout=30
        )

        response.raise_for_status()
        data = response.json()
        
        # Log the full response structure
        print("\nFull API Response:")
        import json
        print(json.dumps(data, indent=2))
        print("\n")

        total_reviews = 0
        weighted_rating_sum = 0
        img_urls = []

        for result in data.get("results", []):
            print(f"\nProcessing result:")
            print(json.dumps(result, indent=2))
            
            content = result.get("content", {})
            print(f"\nContent section:")
            print(json.dumps(content, indent=2))
            
            organic_results = content.get("results", {}).get("organic", [])
            print(f"\nFound {len(organic_results)} organic results")

            for idx, product in enumerate(organic_results):
                print(f"\nProduct {idx + 1}:")
                print(json.dumps(product, indent=2))
                
                # Try multiple possible image fields
                img_url = None
                if product.get("thumbnail"):
                    img_url = product.get("thumbnail")
                    print(f"Found thumbnail URL: {img_url}")
                elif product.get("image"):
                    img_url = product.get("image")
                    print(f"Found image URL: {img_url}")
                elif product.get("images"):
                    images = product.get("images")
                    if isinstance(images, list) and images:
                        img_url = images[0]
                        print(f"Found URL in images array: {img_url}")
                
                if img_url:
                    # Analyze URL structure
                    print(f"URL Analysis:")
                    print(f"- Full URL: {img_url}")
                    print(f"- Starts with http/https: {img_url.startswith(('http://', 'https://'))}")
                    print(f"- URL length: {len(img_url)}")
                    print(f"- URL parts: {img_url.split('/')}")
                    
                    if img_url.startswith(('http://', 'https://')):
                        img_urls.append(img_url)
                        print("✓ URL added to valid images list")
                    else:
                        print("✗ URL rejected - invalid protocol")
                else:
                    print(f"No image found in any field for product {idx + 1}")

                rating = product.get("rating")
                reviews_count = product.get("reviews_count")
                
                if rating is not None and reviews_count is not None:
                    print(f"Rating: {rating}, Reviews: {reviews_count}")
                    total_reviews += reviews_count
                    weighted_rating_sum += rating * reviews_count
                else:
                    print(f"Missing rating or reviews. Rating: {rating}, Reviews: {reviews_count}")

        weighted_avg_rating = round(weighted_rating_sum / total_reviews, 2) if total_reviews > 0 else None

        return {
            "total_reviews": total_reviews,
            "weighted_avg_rating": weighted_avg_rating,
            "img_urls": img_urls,
            "error": None
        }

    except requests.RequestException as e:
        return {
            "total_reviews": 0,
            "weighted_avg_rating": None,
            "img_urls": [],
            "error": f"Error fetching reviews: {str(e)}"
        }
    except Exception as e:
        return {
            "total_reviews": 0,
            "weighted_avg_rating": None,
            "img_urls": [],
            "error": f"Unexpected error: {str(e)}"
        }

# Example usage:
# result = get_product_reviews("apple airpods pro 2")
# print(result)
