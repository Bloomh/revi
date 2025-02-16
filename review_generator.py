import os
import json
from pathlib import Path
import openai
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv('OPENAI_API_KEY')

def generate_review(video_data, transcript):
    """
    Generate a review from video data and transcript using OpenAI.
    
    Args:
        video_data (dict): Video metadata including title, description, etc.
        transcript (str): Video transcript text
    
    Returns:
        dict: Generated review with rating
    """
    # Get platform from video info or default to YouTube
    platform = video_data.get('platform', 'YouTube')
    
    # Create a prompt that includes key video information
    prompt = f"""Based on this {platform} review:
Title: {video_data['title']}
Channel: {video_data['channel']}
Description: {video_data['description']}

Transcript: {transcript}

Write a customer review as if you personally used the product. The review should:
1. Be 1-4 sentences long
2. Include specific details about the product's features and performance
3. Give a rating out of 5 stars
4. Focus on your direct experience with the product
5. NOT mention that this is based on a video or reference any reviewers
6. Be written in first person about your hands-on experience
7. Include both pros and cons

Respond with a JSON object in this exact format, with no deviations:
{{
    "review_text": "Your 1-4 sentence review here",
    "rating": "Your rating out of 5 stars here"
}}

Make sure to:
- Use proper JSON formatting with double quotes
- Make the rating a number between 1 and 5
- Write as a customer who bought and used the product
- Never mention YouTube, videos, or reviewers
- Focus on personal experience with the product"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert at distilling product reviews into concise, authentic summaries."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        content = response.choices[0].message.content
        print("Review generated: ", content)
        
        # Try to extract JSON even if it's embedded in other text
        try:
            # First try direct JSON parsing
            review_data = json.loads(content)
        except json.JSONDecodeError:
            # If that fails, try to find JSON-like structure
            import re
            json_pattern = r'\{[^{}]*\}'  # Simple pattern to match JSON object
            matches = re.findall(json_pattern, content)
            if matches:
                try:
                    review_data = json.loads(matches[0])
                except json.JSONDecodeError:
                    raise Exception("Could not parse embedded JSON")
            else:
                raise Exception("No JSON-like structure found in response")
        
        # Validate the structure
        if not isinstance(review_data, dict):
            raise Exception("Response is not a dictionary")
        if 'review_text' not in review_data or 'rating' not in review_data:
            raise Exception("Missing required fields in response")
            
        # Convert rating to float/int if it's a string
        if isinstance(review_data['rating'], str):
            try:
                review_data['rating'] = float(review_data['rating'])
            except ValueError:
                raise Exception("Rating must be a number")
                
        if not isinstance(review_data['rating'], (int, float)) or not 1 <= float(review_data['rating']) <= 5:
            raise Exception("Invalid rating value")
        if not isinstance(review_data['review_text'], str) or len(review_data['review_text']) < 10:
            raise Exception("Invalid review text")
            
        return review_data
        
    except Exception as e:
        print(f"Error generating review: {str(e)}")
        return None

def process_query_directory(query_dir):
    """
    Process all videos in a query directory and generate reviews.
    
    Args:
        query_dir (str): Path to query directory
    
    Returns:
        list: List of generated reviews
    """
    print(f"\nProcessing directory: {query_dir}")
    query_path = Path(query_dir)
    reviews = []
    
    # Process each video directory
    for video_dir in query_path.iterdir():
        print(f"\nChecking directory: {video_dir}")
        if not video_dir.is_dir():
            print("Not a directory, skipping...")
            continue
            
        video_data_path = video_dir / 'video_data.json'
        print(f"Looking for video data at: {video_data_path}")
        if not video_data_path.exists():
            print("No video data found, skipping...")
            continue
            
        # Load video data
        try:
            print("Loading video data...")
            with open(video_data_path, 'r') as f:
                video_data = json.load(f)
            print(f"Video title: {video_data['video_info']['title']}")
            print(f"Transcript length: {len(video_data.get('transcript', ''))} chars")
                
            # Generate review
            print("Generating review...")
            review = generate_review(
                video_data=video_data['video_info'],
                transcript=video_data.get('transcript', '')
            )
            print("Review generated successfully!")
            
            if review and isinstance(review, dict) and 'review_text' in review and 'rating' in review:
                try:
                    reviews.append({
                        'video_title': video_data['video_info']['title'],
                        'channel': video_data['video_info']['channel'],
                        'review_text': review['review_text'],
                        'rating': review['rating'],
                        'video_url': video_data['video_info']['video_url']
                    })
                    print(f"Added review with rating: {review['rating']} stars")
                except Exception as e:
                    print(f"Error adding review: {str(e)}")
            else:
                print(f"Invalid review format: {review}")
                
        except Exception as e:
            print(f"Error processing {video_dir}: {str(e)}")
            
    return reviews

def save_reviews(query_dir, reviews):
    """
    Save generated reviews to a JSON file.
    
    Args:
        query_dir (str): Path to query directory
        reviews (list): List of generated reviews
    """
    query_path = Path(query_dir)
    reviews_file = query_path / 'generated_reviews.json'
    
    with open(reviews_file, 'w') as f:
        json.dump(reviews, f, indent=2)
    
    print(f"Saved {len(reviews)} reviews to {reviews_file}")

def main(query_dir):
    """
    Main function to generate reviews for all videos in a query directory.
    
    Args:
        query_dir (str): Path to query directory
    """
    # Generate reviews
    reviews = process_query_directory(query_dir)
    
    # Save reviews
    if reviews:
        save_reviews(query_dir, reviews)
    else:
        print("No reviews were generated")

if __name__ == "__main__":
    # You can run this directly with a query directory
    import sys
    if len(sys.argv) > 1:
        query_dir = sys.argv[1]
        main(query_dir)
    else:
        print("Please provide a query directory path")
