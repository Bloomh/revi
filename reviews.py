import requests
from pprint import pprint


payload = {
    'source': 'google_shopping_search',
    'domain': 'com',
    'query': 'apple airpods pro 2',
    'pages': 2,
    'parse': True,
    'context': [
        {'key': 'sort_by', 'value': 'r'},
    ],
}

response = requests.request(
    'POST',
    'https://realtime.oxylabs.io/v1/queries',
    auth=('afry477_X2w0Z', 'DpLGCM3Vk_WhNP_'),
    json=payload,
)

data = response.json()

def extract_reviews_and_rating(data):
    total_reviews = 0
    weighted_rating_sum = 0
    img_url = ""

    for result in data.get("results", []):
        content = result.get("content", {})
        organic_results = content.get("results", {}).get("organic", [])

        if organic_results:
            img_url = organic_results[0].get("thumbnail")

        for product in organic_results:
            rating = product.get("rating")
            reviews_count = product.get("reviews_count")

            if rating is not None and reviews_count is not None:
                total_reviews += reviews_count
                weighted_rating_sum += rating * reviews_count

    weighted_avg_rating = (weighted_rating_sum / total_reviews) if total_reviews > 0 else None

    return {
        "total_reviews": total_reviews,
        "weighted_avg_rating": weighted_avg_rating,
        "img_url": img_url
    }

result = extract_reviews_and_rating(data)

pprint(result)
