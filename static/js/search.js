document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const loadingOverlay = document.getElementById('loading-overlay');
    
    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const query = document.getElementById('product-search').value;
        
        try {
            // Show loading overlay
            loadingOverlay.classList.add('visible');
            console.log('Loading overlay shown');
            
            // Make the request
            const response = await fetch(`/search?product=${encodeURIComponent(query)}`);
            const html = await response.text();
            
            // Update the page content
            document.documentElement.innerHTML = html;
            
            // Update the URL
            history.pushState({}, '', `/search?product=${encodeURIComponent(query)}`);
            
            console.log('Search completed');
        } catch (error) {
            console.error('Search error:', error);
            loadingOverlay.classList.remove('visible');
        }
    });
});
