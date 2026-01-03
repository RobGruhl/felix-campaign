/**
 * Comic Reader - Main navigation and display logic
 */

class ComicReader {
    constructor() {
        this.pages = [];
        this.currentPageIndex = 0;
        this.viewMode = 'single'; // 'single' or 'grid'
        this.zoomMode = 'fit-screen'; // 'fit-screen', 'fit-width', '100', '150'
        this.isLoading = false;
    }

    async init() {
        try {
            // Load page metadata
            const response = await fetch('data/pages.json');
            if (!response.ok) {
                throw new Error('Failed to load pages data');
            }
            const data = await response.json();
            this.pages = data.pages || data;

            // Initialize UI
            this.setupControls();
            this.setupKeyboardShortcuts();
            this.setupTouchGestures();
            this.setupBrowserNavigation();
            this.loadPageFromURL();
            this.updateDisplay();
            this.preloadAdjacentPages();

            // Generate thumbnail grid
            this.generateThumbnailGrid();

            // Update total pages display
            document.getElementById('total-pages').textContent = this.pages.length - 1; // Subtract cover

        } catch (error) {
            console.error('Failed to initialize reader:', error);
            this.showError('Failed to load comic data. Please refresh the page.');
        }
    }

    setupControls() {
        // Navigation buttons
        document.getElementById('first-page').addEventListener('click', () => this.goToFirstPage());
        document.getElementById('prev-page').addEventListener('click', () => this.previousPage());
        document.getElementById('next-page').addEventListener('click', () => this.nextPage());
        document.getElementById('last-page').addEventListener('click', () => this.goToLastPage());

        // View toggle buttons
        document.getElementById('view-single').addEventListener('click', () => this.switchView('single'));
        document.getElementById('view-grid').addEventListener('click', () => this.switchView('grid'));
        document.getElementById('toggle-grid-view').addEventListener('click', () => this.switchView('grid'));
        document.getElementById('close-grid').addEventListener('click', () => this.switchView('single'));

        // Zoom controls
        document.getElementById('zoom-fit').addEventListener('click', () => this.setZoom('fit-screen'));
        document.getElementById('zoom-width').addEventListener('click', () => this.setZoom('fit-width'));
        document.getElementById('zoom-100').addEventListener('click', () => this.setZoom('100'));
        document.getElementById('zoom-150').addEventListener('click', () => this.setZoom('150'));

        // Click image to toggle zoom
        const pageDisplay = document.querySelector('.page-display');
        const img = document.getElementById('main-page-image');
        img.addEventListener('click', () => this.toggleImageZoom());
    }

    setZoom(mode) {
        this.zoomMode = mode;
        const pageDisplay = document.querySelector('.page-display');
        const img = document.getElementById('main-page-image');
        const zoomLevel = document.getElementById('zoom-level');

        // Remove all zoom classes
        pageDisplay.classList.remove('fit-screen', 'fit-width', 'fit-height', 'zoomed');
        img.style.transform = '';
        img.style.width = '';
        img.style.height = '';

        // Update button states
        document.querySelectorAll('.zoom-btn').forEach(btn => btn.classList.remove('active'));

        switch(mode) {
            case 'fit-screen':
                pageDisplay.classList.add('fit-screen');
                document.getElementById('zoom-fit').classList.add('active');
                zoomLevel.textContent = 'Click image to zoom';
                break;
            case 'fit-width':
                pageDisplay.classList.add('fit-width');
                document.getElementById('zoom-width').classList.add('active');
                zoomLevel.textContent = 'Fit to width';
                break;
            case '100':
                pageDisplay.classList.add('zoomed');
                document.getElementById('zoom-100').classList.add('active');
                zoomLevel.textContent = '100% - scroll to pan';
                break;
            case '150':
                pageDisplay.classList.add('zoomed');
                img.style.transform = 'scale(1.5)';
                img.style.transformOrigin = 'top center';
                document.getElementById('zoom-150').classList.add('active');
                zoomLevel.textContent = '150% - scroll to pan';
                break;
        }
    }

    toggleImageZoom() {
        // Toggle between fit-screen and 100% zoom
        if (this.zoomMode === 'fit-screen' || this.zoomMode === 'fit-width') {
            this.setZoom('100');
        } else {
            this.setZoom('fit-screen');
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger if user is typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            switch(e.key) {
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    e.preventDefault();
                    this.previousPage();
                    break;
                case 'ArrowRight':
                case 'd':
                case 'D':
                    e.preventDefault();
                    this.nextPage();
                    break;
                case 'Home':
                    e.preventDefault();
                    this.goToFirstPage();
                    break;
                case 'End':
                    e.preventDefault();
                    this.goToLastPage();
                    break;
                case 'g':
                case 'G':
                    e.preventDefault();
                    this.toggleView();
                    break;
                case 'f':
                case 'F':
                    e.preventDefault();
                    this.setZoom('fit-screen');
                    break;
                case 'w':
                case 'W':
                    e.preventDefault();
                    this.setZoom('fit-width');
                    break;
                case '1':
                    e.preventDefault();
                    this.setZoom('100');
                    break;
                case '2':
                    e.preventDefault();
                    this.setZoom('150');
                    break;
            }
        });
    }

    setupTouchGestures() {
        let touchStartX = 0;
        let touchStartY = 0;
        const pageDisplay = document.querySelector('.page-display');

        pageDisplay.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        }, { passive: true });

        pageDisplay.addEventListener('touchend', (e) => {
            // Don't navigate when zoomed - user is panning the image
            if (this.zoomMode === '100' || this.zoomMode === '150') {
                return;
            }

            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;

            const diffX = touchStartX - touchEndX;
            const diffY = touchStartY - touchEndY;

            // Only trigger if horizontal swipe is dominant
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
                if (diffX > 0) {
                    this.nextPage(); // Swipe left
                } else {
                    this.previousPage(); // Swipe right
                }
            }
        }, { passive: true });
    }

    setupBrowserNavigation() {
        // Handle browser back/forward buttons
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.page !== undefined) {
                const pageIndex = this.pages.findIndex(p => p.page === e.state.page);
                if (pageIndex !== -1) {
                    this.currentPageIndex = pageIndex;
                    this.updateDisplay(false); // Don't push state again
                    this.preloadAdjacentPages();
                }
            }
        });
    }

    loadPageFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const pageParam = urlParams.get('page');

        if (pageParam !== null) {
            const pageNum = parseInt(pageParam);
            const pageIndex = this.pages.findIndex(p => p.page === pageNum);
            if (pageIndex !== -1) {
                this.currentPageIndex = pageIndex;
            }
        }
    }

    goToPage(pageIndex, pushState = true) {
        if (pageIndex < 0 || pageIndex >= this.pages.length) return;

        this.currentPageIndex = pageIndex;
        this.updateDisplay(pushState);
        this.preloadAdjacentPages();

        // Scroll to top on page change
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    goToFirstPage() {
        this.goToPage(0);
    }

    goToLastPage() {
        this.goToPage(this.pages.length - 1);
    }

    previousPage() {
        if (this.currentPageIndex > 0) {
            this.goToPage(this.currentPageIndex - 1);
        }
    }

    nextPage() {
        if (this.currentPageIndex < this.pages.length - 1) {
            this.goToPage(this.currentPageIndex + 1);
        }
    }

    updateDisplay(pushState = true) {
        const page = this.pages[this.currentPageIndex];
        const img = document.getElementById('main-page-image');

        // Update image
        img.src = page.image;
        img.alt = page.title;

        // Update page info
        const pageNum = page.page === 0 ? 'Cover' : page.page;
        document.getElementById('current-page').textContent = pageNum;
        document.getElementById('page-title').textContent = page.title;

        // Update browser title
        document.title = `${page.title} - Graphic Novel`;

        // Update button states
        this.updateButtonStates();

        // Update page metadata
        this.updatePageMetadata(page);

        // Update URL if requested
        if (pushState) {
            this.updateURL();
        }
    }

    updateButtonStates() {
        const firstBtn = document.getElementById('first-page');
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        const lastBtn = document.getElementById('last-page');

        // Disable first/prev on first page
        firstBtn.disabled = this.currentPageIndex === 0;
        prevBtn.disabled = this.currentPageIndex === 0;

        // Disable next/last on last page
        nextBtn.disabled = this.currentPageIndex === this.pages.length - 1;
        lastBtn.disabled = this.currentPageIndex === this.pages.length - 1;
    }

    updatePageMetadata(page) {
        const charactersDiv = document.getElementById('page-characters');
        const locationsDiv = document.getElementById('page-locations');

        // Update characters
        if (page.characters && page.characters.length > 0) {
            charactersDiv.innerHTML = `<strong>Characters:</strong> ${page.characters.join(', ')}`;
            charactersDiv.style.display = 'block';
        } else {
            charactersDiv.style.display = 'none';
        }

        // Update locations
        if (page.locations && page.locations.length > 0) {
            locationsDiv.innerHTML = `<strong>Location:</strong> ${page.locations.join(', ')}`;
            locationsDiv.style.display = 'block';
        } else {
            locationsDiv.style.display = 'none';
        }
    }

    updateURL() {
        const page = this.pages[this.currentPageIndex];
        const newURL = `${window.location.pathname}?page=${page.page}`;
        history.pushState(
            { page: page.page },
            '',
            newURL
        );
    }

    preloadAdjacentPages() {
        // Remove old preload links
        document.querySelectorAll('link[rel="prefetch"]').forEach(link => link.remove());

        // Preload next and previous pages
        const preloadIndexes = [
            this.currentPageIndex - 1,
            this.currentPageIndex + 1
        ];

        preloadIndexes.forEach(idx => {
            if (idx >= 0 && idx < this.pages.length) {
                const link = document.createElement('link');
                link.rel = 'prefetch';
                link.href = this.pages[idx].image;
                document.head.appendChild(link);
            }
        });
    }

    switchView(mode) {
        this.viewMode = mode;

        const singleView = document.getElementById('single-view');
        const gridView = document.getElementById('grid-view');
        const singleBtn = document.getElementById('view-single');
        const gridBtn = document.getElementById('view-grid');

        if (mode === 'single') {
            singleView.classList.add('active');
            gridView.classList.remove('active');
            singleBtn.classList.add('active');
            gridBtn.classList.remove('active');
        } else {
            singleView.classList.remove('active');
            gridView.classList.add('active');
            singleBtn.classList.remove('active');
            gridBtn.classList.add('active');
        }
    }

    toggleView() {
        this.switchView(this.viewMode === 'single' ? 'grid' : 'single');
    }

    generateThumbnailGrid() {
        const grid = document.getElementById('thumbnail-grid');
        grid.innerHTML = this.pages.map((page, idx) => `
            <div class="thumbnail-item" data-page="${idx}">
                <img src="${page.thumbnail}"
                     alt="${page.title}"
                     loading="lazy">
                <div class="thumbnail-label">
                    <div class="thumbnail-title">${page.title}</div>
                    <div class="thumbnail-number">Page ${page.page === 0 ? 'Cover' : page.page}</div>
                </div>
            </div>
        `).join('');

        // Add click handlers
        grid.querySelectorAll('.thumbnail-item').forEach(item => {
            item.addEventListener('click', () => {
                const pageIdx = parseInt(item.dataset.page);
                this.goToPage(pageIdx);
                this.switchView('single');
            });
        });
    }

    showError(message) {
        const container = document.querySelector('.reader-container');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <h2>Error</h2>
            <p>${message}</p>
        `;
        container.innerHTML = '';
        container.appendChild(errorDiv);
    }
}

// Initialize reader when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.reader = new ComicReader();
    window.reader.init();
});
