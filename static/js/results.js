document.addEventListener('DOMContentLoaded', function() {
    // Set up image loading handlers
    const productImage = document.querySelector('.product-image');

    if (productImage) {
        // Handle successful image load
        productImage.addEventListener('load', function() {
            this.classList.add('loaded');
        });

        // Handle image load error
        productImage.addEventListener('error', function() {
            this.style.display = 'none';
            const wrapper = document.querySelector('.single-image-wrapper');
            if (wrapper) {
                wrapper.innerHTML = `
                    <div class="no-image">
                        <i class="fas fa-image"></i>
                        <span>No images available</span>
                    </div>
                `;
            }
        });

        // If image is already loaded (from cache)
        if (productImage.complete) {
            productImage.classList.add('loaded');
        }
    }

    // Handle form submission
    const searchForm = document.querySelector('.search-form');
    const loadingOverlay = document.getElementById('loading-overlay');
    
    if (searchForm) {
        searchForm.addEventListener('submit', function() {
            loadingOverlay.classList.add('visible');
        });
    }
});
