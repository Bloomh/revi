from pathlib import Path
from datetime import datetime

DOWNLOADS_DIR = Path('downloads')

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
