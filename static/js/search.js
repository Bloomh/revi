document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.querySelector('.loader p');
    
    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const query = document.getElementById('product-search').value;
        
        try {
            // Show loading overlay
            loadingOverlay.classList.add('visible');
            loadingText.textContent = 'Searching for reviews...';
            
            // Show processing message
            loadingText.textContent = 'Analyzing reviews...';
            
            // Make the request with AJAX header
            const response = await fetch(`/search?product=${encodeURIComponent(query)}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Hide loading overlay
                loadingOverlay.classList.remove('visible');
                
                // Update URL without reloading
                window.history.pushState({}, '', `/search?product=${encodeURIComponent(query)}`);
                
                // Update page content
                document.body.innerHTML = `
                    <div class="container">
                        <header class="header results-header-position">
                            <a href="/" class="logo">
                                <h1>Revi</h1>
                            </a>
                        </header>
                        
                        <main class="results-section">
                        <div class="results-header">
                            <h2>Results for "${query}"</h2>
                            <div class="results-summary">
                                <div class="product-info">
                                    <div class="product-image-container">
                                        <div class="no-image">
                                            <i class="fas fa-image"></i>
                                            <span>No images available</span>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="rating-card">
                                    <div class="rating-header">
                                        <div class="stars">
                                            ${Array(5).fill().map((_, i) => {
                                                const rating = data.weighted_avg_rating;
                                                if (rating - i >= 1) return '<i class="fas fa-star"></i>';
                                                if (rating - i > 0) return '<i class="fas fa-star-half-alt"></i>';
                                                return '<i class="far fa-star"></i>';
                                            }).join('')}
                                        </div>
                                        <div class="rating-number">${data.weighted_avg_rating.toFixed(1)}</div>
                                    </div>
                                    
                                    <div class="rating-stats">
                                        <div class="stat-item">
                                            <span class="stat-label">Total Reviews</span>
                                            <span class="stat-value">${data.total_reviews.toLocaleString()}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="youtube-reviews">
                            <div class="reviews-grid">
                                ${data.reviews.map(review => `
                                    <div class="review-card">
                                        <div class="review-header">
                                            <div class="review-rating">
                                                ${Array(5).fill().map((_, i) => 
                                                    i < Math.round(review.rating) ? 
                                                    '<i class="fas fa-star"></i>' : 
                                                    '<i class="far fa-star"></i>'
                                                ).join('')}
                                            </div>
                                            <a href="${review.video_url}" target="_blank" class="youtube-link">
                                                <i class="fab fa-youtube"></i>
                                                <span>Watch on YouTube</span>
                                            </a>
                                        </div>
                                        <div class="review-content">
                                            <p>${review.review_text}</p>
                                        </div>
                                        <div class="review-source">
                                            <i class="fas fa-user"></i>
                                            <span>${review.channel || 'YouTube Creator'}</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                        </main>
                        
                        <div class="search-again-container">
                            <a href="/" class="search-again-button">
                                <i class="fas fa-search"></i>
                                Search Again
                            </a>
                        </div>
                        
                        <footer class="footer">
                            <p>TreeHacks 2025 | Made by Henry Bloom & Alexis Fry</p>
                        </footer>
                    </div>
                    
                    <div id="loading-overlay" class="loading-overlay">
                        <div class="loader">
                            <div class="spinner"></div>
                            <div id="loading-text" class="loading-text">Loading...</div>
                        </div>
                    </div>
                `;
            } else {
                throw new Error(data.message || 'Error processing request');
            }
            
        } catch (error) {
            console.error('Search error:', error);
            loadingOverlay.classList.remove('visible');
            
            // Show error message
            const mainContent = document.querySelector('main');
            mainContent.innerHTML = `
                <div class="error-message">
                    <h2>Error</h2>
                    <p>${error.message || 'An error occurred while processing your request'}</p>
                </div>
            `;
        }
    });
});
