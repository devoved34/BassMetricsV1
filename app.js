/**
 * BassMetrics Dashboard - Advanced Application Logic
 * Handles section switching, data management, voting, and user interactions
 */

class BassMetricsApp {
    constructor() {
        this.currentSection = 'charts';
        this.currentUser = null;
        this.isVerified = false;
        this.votingTracks = [];
        this.userVotes = new Map();
        
        // View states for different chart types
        this.chartViews = {
            algorithm: 'mainstream',
            community: 'overall'
        };
        
        // Cache for API responses
        this.cache = new Map();
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.checkAuthStatus();
    }

    setupEventListeners() {
        // Navigation between sections
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchSection(e.target.dataset.section);
            });
        });

        // Chart toggle buttons
        document.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleChartToggle(e));
        });

        // Artist verification
        const artistInput = document.getElementById('artist-name');
        if (artistInput) {
            let debounceTimer;
            artistInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.checkArtistVerification(e.target.value);
                }, 500);
            });
        }

        // Forms
        this.setupFormHandlers();
        
        // Authentication
        this.setupAuthHandlers();
        
        // Voting interactions
        this.setupVotingHandlers();
    }

    setupFormHandlers() {
        // Verification form
        const verificationForm = document.getElementById('verification-form');
        if (verificationForm) {
            verificationForm.addEventListener('submit', (e) => this.handleVerification(e));
        }

        // Submission form
        const submissionForm = document.getElementById('submission-form');
        if (submissionForm) {
            submissionForm.addEventListener('submit', (e) => this.handleTrackSubmission(e));
        }

        // Vote search
        const voteSearch = document.getElementById('vote-search');
        if (voteSearch) {
            voteSearch.addEventListener('input', (e) => this.handleVoteSearch(e.target.value));
        }

        // Load voting tracks button
        const loadVotingBtn = document.getElementById('load-voting-tracks');
        if (loadVotingBtn) {
            loadVotingBtn.addEventListener('click', () => this.loadVotingTracks());
        }
    }

    setupAuthHandlers() {
        // Show/hide auth forms
        const showRegister = document.getElementById('show-register');
        const showLogin = document.getElementById('show-login');
        
        if (showRegister) {
            showRegister.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleAuthForms('register');
            });
        }
        
        if (showLogin) {
            showLogin.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleAuthForms('login');
            });
        }

        // Auth form submissions
        const loginForm = document.querySelector('#login-form form');
        const registerForm = document.querySelector('#register-form form');
        const logoutBtn = document.getElementById('logout-btn');

        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
        
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => this.handleRegister(e));
        }
        
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }
    }

    setupVotingHandlers() {
        // Event delegation for voting controls
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('vote-track-btn')) {
                this.handleTrackVote(e.target.dataset.trackId);
            }
            
            if (e.target.classList.contains('play-btn')) {
                this.handlePlayTrack(e.target.dataset.trackId);
            }
        });

        // Range input handlers for component voting
        document.addEventListener('input', (e) => {
            if (e.target.type === 'range' && e.target.dataset.component) {
                this.updateVoteDisplay(e.target);
            }
        });
    }

    // Section Management
    switchSection(sectionName) {
        // Hide all sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Show selected section
        const targetSection = document.getElementById(sectionName);
        const targetNavBtn = document.querySelector(`[data-section="${sectionName}"]`);
        
        if (targetSection && targetNavBtn) {
            targetSection.classList.add('active');
            targetNavBtn.classList.add('active');
            this.currentSection = sectionName;
            
            // Load section-specific data
            this.loadSectionData(sectionName);
        }
    }

    loadSectionData(sectionName) {
        switch(sectionName) {
            case 'charts':
                this.loadAllCharts();
                break;
            case 'vote':
                this.loadVotingTracks();
                break;
            case 'profile':
                this.updateProfileStats();
                break;
        }
    }

    // Chart Management
    handleChartToggle(event) {
        const button = event.target;
        const view = button.dataset.view;
        const chartType = button.dataset.chart;
        
        // Update button states
        const parent = button.closest('.panel-header');
        parent.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');
        
        // Update view state and reload chart
        this.chartViews[chartType] = view;
        this.loadChart(chartType, view);
    }

    async loadAllCharts() {
        this.showLoading();
        
        try {
            await Promise.all([
                this.loadChart('algorithm', this.chartViews.algorithm),
                this.loadChart('community', this.chartViews.community),
                this.loadUndergroundTracks(),
                this.loadRisingTracks()
            ]);
        } catch (error) {
            this.showError('Failed to load charts');
            console.error('Chart loading error:', error);
        } finally {
            this.hideLoading();
        }
    }

    async loadChart(type, view) {
        try {
            // Check cache first
            const cacheKey = `${type}-${view}`;
            if (this.cache.has(cacheKey)) {
                this.renderChart(type, this.cache.get(cacheKey));
                return;
            }

            // Simulate API call with sophisticated mock data
            const tracks = this.generateMockTracks(type, 20);
            
            // Cache the result
            this.cache.set(cacheKey, tracks);
            
            this.renderChart(type, tracks);
        } catch (error) {
            console.error(`Failed to load ${type} chart:`, error);
            this.showError(`Failed to load ${type} chart`);
        }
    }

    async loadUndergroundTracks() {
        const tracks = this.generateMockTracks('underground', 10);
        this.renderTrackList('underground-tracks', tracks, 'underground');
    }

    async loadRisingTracks() {
        const tracks = this.generateMockTracks('rising', 10);
        this.renderTrackList('rising-tracks', tracks, 'rising');
    }

    renderChart(type, tracks) {
        const containerId = `${type}-tracks`;
        this.renderTrackList(containerId, tracks, type);
    }

    renderTrackList(containerId, tracks, listType) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = tracks.map((track, index) => `
            <div class="track-card ${listType}" data-track-id="${track.id}">
                <div class="track-rank">${index + 1}</div>
                <div class="track-artwork artwork-placeholder">
                    <span>🎵</span>
                </div>
                <div class="track-info">
                    <div class="track-title">${track.title}</div>
                    <div class="track-artist">${track.artist}</div>
                    <div class="track-platforms">
                        ${track.platforms.map(platform => 
                            `<span class="platform-badge ${platform}" title="${platform}"></span>`
                        ).join('')}
                    </div>
                    <div class="track-stats">
                        ${this.renderTrackStats(track, listType)}
                    </div>
                </div>
                <div class="track-trend ${track.trend}">${this.getTrendIcon(track.trend)}</div>
                <div class="track-actions">
                    <button class="play-btn" data-track-id="${track.id}" title="Play ${track.title}">
                        ▶
                    </button>
                    ${listType === 'community' ? 
                        `<button class="vote-btn floating" data-track-id="${track.id}">Vote</button>` : 
                        ''
                    }
                </div>
            </div>
        `).join('');
    }

    renderTrackStats(track, listType) {
        if (listType === 'algorithm' || listType === 'underground' || listType === 'rising') {
            return `
                <span class="stat">▶️ ${track.plays}</span>
                <span class="stat">❤️ ${track.likes}</span>
                <span class="stat">📈 ${track.score}</span>
            `;
        } else if (listType === 'community') {
            return `
                <span class="stat">Drop: ${track.dropQuality}/10</span>
                <span class="stat">Prod: ${track.production}/10</span>
                <span class="stat">Bass: ${track.bassQuality}/10</span>
                <span class="stat">👥 ${track.voteCount} votes</span>
            `;
        }
        return '';
    }

    getTrendIcon(trend) {
        const icons = {
            'up': '↗️',
            'down': '↘️',
            'stable': '➡️'
        };
        return icons[trend] || '➡️';
    }

    // Artist Verification
    async checkArtistVerification(artistName) {
        const statusDiv = document.getElementById('verification-status');
        const submitBtn = document.getElementById('submit-btn');
        
        if (!artistName || artistName.length < 2) {
            statusDiv.innerHTML = '';
            submitBtn.disabled = true;
            return;
        }

        statusDiv.innerHTML = '⏳ Checking verification...';
        statusDiv.className = 'verification-status checking';

        try {
            // Simulate API call
            await this.delay(800);
            
            const isVerified = Math.random() > 0.3; // 70% chance of verification
            const followers = Math.floor(Math.random() * 100000) + 10000;
            const monthlyListeners = Math.floor(Math.random() * 500000) + 50000;
            
            if (isVerified && followers > 5000) {
                statusDiv.className = 'verification-status verified';
                statusDiv.innerHTML = `
                    ✅ Verified Artist
                    <div class="verification-details">
                        📊 ${monthlyListeners.toLocaleString()} monthly listeners<br>
                        👥 ${followers.toLocaleString()} followers<br>
                        ⏰ Account active for 18+ months
                    </div>
                `;
                submitBtn.disabled = false;
                this.isVerified = true;
            } else {
                statusDiv.className = 'verification-status unverified';
                statusDiv.innerHTML = `
                    ❌ Not Verified
                    <div class="verification-requirements">
                        Requirements: 5,000+ followers, 18+ months active<br>
                        Current: ${followers.toLocaleString()} followers
                    </div>
                `;
                submitBtn.disabled = true;
                this.isVerified = false;
            }
        } catch (error) {
            statusDiv.className = 'verification-status error';
            statusDiv.innerHTML = '❌ Verification check failed';
            submitBtn.disabled = true;
        }
    }

    async handleVerification(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData);
        
        this.showLoading();
        
        try {
            // Simulate API call
            await this.delay(1500);
            
            this.showSuccess('Verification submitted successfully!');
            this.checkArtistVerification(data['artist-name']);
        } catch (error) {
            this.showError('Verification failed: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async handleTrackSubmission(event) {
        event.preventDefault();
        
        if (!this.isVerified) {
            this.showError('Please verify your artist profile first');
            return;
        }

        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData);
        
        // Get platform links
        data.platformLinks = {
            soundcloud: document.getElementById('soundcloud-link').value,
            spotify: document.getElementById('spotify-link').value,
            youtube: document.getElementById('youtube-link').value
        };

        this.showLoading();
        
        try {
            // Simulate API call
            await this.delay(2000);
            
            this.showSuccess('Track submitted successfully! It will appear in voting queues shortly.');
            event.target.reset();
            document.getElementById('verification-status').innerHTML = '';
            this.isVerified = false;
            document.getElementById('submit-btn').disabled = true;
        } catch (error) {
            this.showError('Track submission failed: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    // Voting System
    async loadVotingTracks() {
        this.showLoading();
        
        try {
            this.votingTracks = this.generateMockTracks('voting', 5);
            this.renderVotingTracks();
        } catch (error) {
            this.showError('Failed to load voting tracks');
        } finally {
            this.hideLoading();
        }
    }

    renderVotingTracks() {
        const container = document.getElementById('voting-tracks');
        if (!container) return;

        container.innerHTML = this.votingTracks.map(track => `
            <div class="voting-track-item" data-track-id="${track.id}">
                <div class="track-header">
                    <div class="track-artwork artwork-placeholder">🎵</div>
                    <div class="track-details">
                        <h4>${track.title}</h4>
                        <p>${track.artist}</p>
                        <div class="track-platforms">
                            ${track.platforms.map(platform => 
                                `<span class="platform-badge ${platform}"></span>`
                            ).join('')}
                        </div>
                    </div>
                </div>
                
                <div class="voting-controls">
                    <div class="vote-category">
                        <label>Drop Quality (1-10)</label>
                        <input type="range" min="1" max="10" value="5" 
                               data-track="${track.id}" data-component="dropQuality">
                        <span class="score-display">5</span>
                    </div>
                    <div class="vote-category">
                        <label>Production Quality (1-10)</label>
                        <input type="range" min="1" max="10" value="5" 
                               data-track="${track.id}" data-component="production">
                        <span class="score-display">5</span>
                    </div>
                    <div class="vote-category">
                        <label>Bass Quality (1-10)</label>
                        <input type="range" min="1" max="10" value="5" 
                               data-track="${track.id}" data-component="bassQuality">
                        <span class="score-display">5</span>
                    </div>
                    <div class="vote-category">
                        <label>Overall Rating (1-10)</label>
                        <input type="range" min="1" max="10" value="5" 
                               data-track="${track.id}" data-component="overall">
                        <span class="score-display">5</span>
                    </div>
                    
                    <button class="vote-track-btn btn btn-primary" data-track-id="${track.id}">
                        Submit Vote
                    </button>
                </div>
                
                <div class="embedded-player">
                    ${this.createEmbeddedPlayer(track)}
                </div>
            </div>
        `).join('');

        // Add range input listeners
        container.querySelectorAll('input[type="range"]').forEach(input => {
            input.addEventListener('input', (e) => this.updateVoteDisplay(e.target));
        });
    }

    updateVoteDisplay(rangeInput) {
        const scoreDisplay = rangeInput.nextElementSibling;
        if (scoreDisplay && scoreDisplay.classList.contains('score-display')) {
            scoreDisplay.textContent = rangeInput.value;
        }
    }

    async handleTrackVote(trackId) {
        if (!this.currentUser) {
            this.showError('Please login to vote');
            this.switchSection('profile');
            return;
        }

        const voteData = {};
        const inputs = document.querySelectorAll(`input[data-track="${trackId}"]`);
        
        inputs.forEach(input => {
            voteData[input.dataset.component] = parseInt(input.value);
        });

        this.showLoading();
        
        try {
            // Simulate API call
            await this.delay(1000);
            
            // Store vote locally
            this.userVotes.set(trackId, voteData);
            
            this.showSuccess('Vote submitted successfully!');
            
            // Update user stats
            this.updateUserStats('votes', 1);
            
            // Optionally remove voted track or disable voting
            const voteButton = document.querySelector(`[data-track-id="${trackId}"].vote-track-btn`);
            if (voteButton) {
                voteButton.disabled = true;
                voteButton.textContent = 'Voted!';
            }
        } catch (error) {
            this.showError('Vote submission failed: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    handleVoteSearch(query) {
        // Filter voting tracks based on search query
        const filtered = this.votingTracks.filter(track => 
            track.title.toLowerCase().includes(query.toLowerCase()) ||
            track.artist.toLowerCase().includes(query.toLowerCase())
        );
        
        // Re-render with filtered results
        this.renderFilteredVotingTracks(filtered);
    }

    createEmbeddedPlayer(track) {
        if (track.platforms.includes('soundcloud')) {
            return `
                <div class="player-placeholder">
                    🎵 SoundCloud Player
                    <button class="play-btn" data-track-id="${track.id}">▶ Preview</button>
                </div>
            `;
        } else if (track.platforms.includes('youtube')) {
            return `
                <div class="player-placeholder">
                    📺 YouTube Player
                    <button class="play-btn" data-track-id="${track.id}">▶ Preview</button>
                </div>
            `;
        }
        return '<div class="player-placeholder">No preview available</div>';
    }

    handlePlayTrack(trackId) {
        const playBtn = document.querySelector(`[data-track-id="${trackId}"].play-btn`);
        if (!playBtn) return;
        
        // Simulate play/pause
        if (playBtn.textContent === '▶') {
            playBtn.textContent = '⏸';
            playBtn.style.boxShadow = '0 0 20px rgba(255, 0, 0, 0.8)';
            
            // Auto-stop after 30 seconds
            setTimeout(() => {
                playBtn.textContent = '▶';
                playBtn.style.boxShadow = '';
            }, 30000);
        } else {
            playBtn.textContent = '▶';
            playBtn.style.boxShadow = '';
        }
    }

    // Authentication
    toggleAuthForms(formType) {
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');
        
        if (formType === 'register') {
            loginForm.classList.add('hidden');
            registerForm.classList.remove('hidden');
        } else {
            registerForm.classList.add('hidden');
            loginForm.classList.remove('hidden');
        }
    }

    async handleLogin(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        const credentials = Object.fromEntries(formData);
        
        this.showLoading();
        
        try {
            // Simulate API call
            await this.delay(1500);
            
            // Mock successful login
            this.currentUser = {
                username: credentials.username,
                email: `${credentials.username}@example.com`,
                votesCast: Math.floor(Math.random() * 100),
                tracksSubmitted: Math.floor(Math.random() * 10),
                trustScore: Math.floor(Math.random() * 50) + 50
            };
            
            this.showUserProfile();
            this.showSuccess(`Welcome back, ${this.currentUser.username}!`);
        } catch (error) {
            this.showError('Login failed: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async handleRegister(event) {
        event.preventDefault();
        const formData = new FormData(event.target);
        const userData = Object.fromEntries(formData);
        
        this.showLoading();
        
        try {
            // Simulate API call
            await this.delay(2000);
            
            // Mock successful registration
            this.currentUser = {
                username: userData.username,
                email: userData.email,
                votesCast: 0,
                tracksSubmitted: 0,
                trustScore: 100
            };
            
            this.showUserProfile();
            this.showSuccess(`Account created successfully! Welcome, ${this.currentUser.username}!`);
        } catch (error) {
            this.showError('Registration failed: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    handleLogout() {
        this.currentUser = null;
        this.userVotes.clear();
        this.hideUserProfile();
        this.showSuccess('Logged out successfully');
    }

    showUserProfile() {
        const authContainer = document.getElementById('auth-container');
        const userProfile = document.getElementById('user-profile');
        const usernameSpan = document.getElementById('username');
        
        if (authContainer) authContainer.classList.add('hidden');
        if (userProfile) userProfile.classList.remove('hidden');
        if (usernameSpan) usernameSpan.textContent = this.currentUser.username;
        
        this.updateProfileStats();
    }

    hideUserProfile() {
        const authContainer = document.getElementById('auth-container');
        const userProfile = document.getElementById('user-profile');
        
        if (userProfile) userProfile.classList.add('hidden');
        if (authContainer) authContainer.classList.remove('hidden');
    }

    updateProfileStats() {
        if (!this.currentUser) return;
        
        const votesCast = document.getElementById('votes-cast');
        const tracksSubmitted = document.getElementById('tracks-submitted');
        const trustScore = document.getElementById('trust-score');
        
        if (votesCast) votesCast.textContent = this.currentUser.votesCast;
        if (tracksSubmitted) tracksSubmitted.textContent = this.currentUser.tracksSubmitted;
        if (trustScore) trustScore.textContent = this.currentUser.trustScore;
    }

    updateUserStats(type, increment) {
        if (!this.currentUser) return;
        
        switch(type) {
            case 'votes':
                this.currentUser.votesCast += increment;
                break;
            case 'tracks':
                this.currentUser.tracksSubmitted += increment;
                break;
        }
        
        this.updateProfileStats();
    }

    checkAuthStatus() {
        // Check for stored authentication (would normally be JWT or session)
        const storedUser = localStorage.getItem('bassMetricsUser');
        if (storedUser) {
            try {
                this.currentUser = JSON.parse(storedUser);
                this.showUserProfile();
            } catch (error) {
                localStorage.removeItem('bassMetricsUser');
            }
        }
    }

    // Utility Functions
    generateMockTracks(type, count) {
        const genres = ['Dubstep', 'Riddim', 'Melodic Dubstep', 'Future Bass', 'Trap'];
        const platforms = ['spotify', 'youtube', 'soundcloud'];
        const trends = ['up', 'down', 'stable'];
        
        return Array.from({length: count}, (_, i) => {
            const trackType = type === 'voting' ? 'Track' : `${type.charAt(0).toUpperCase() + type.slice(1)} Track`;
            
            return {
                id: `${type}-${i + 1}`,
                title: `${trackType} ${i + 1}`,
                artist: `Artist ${i + 1}`,
                genre: genres[Math.floor(Math.random() * genres.length)],
                platforms: this.getRandomPlatforms(platforms),
                plays: this.generateRandomMetric('plays'),
                likes: this.generateRandomMetric('likes'),
                score: (Math.random() * 40 + 60).toFixed(1),
                dropQuality: (Math.random() * 3 + 7).toFixed(1),
                production: (Math.random() * 3 + 7).toFixed(1),
                bassQuality: (Math.random() * 3 + 7).toFixed(1),
                voteCount: Math.floor(Math.random() * 5000) + 500,
                trend: trends[Math.floor(Math.random() * trends.length)]
            };
        });
    }

    getRandomPlatforms(allPlatforms) {
        const count = Math.floor(Math.random() * 3) + 1;
        const shuffled = [...allPlatforms].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    }

    generateRandomMetric(type) {
        if (type === 'plays') {
            const num = Math.random() * 2 + 0.5;
            return num >= 1 ? `${num.toFixed(1)}M` : `${(num * 1000).toFixed(0)}K`;
        } else {
            const num = Math.floor(Math.random() * 100) + 10;
            return `${num}K`;
        }
    }

    // UI Helpers
    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.classList.remove('hidden');
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.classList.add('hidden');
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        // Remove existing notifications
        const existing = document.querySelectorAll('.notification');
        existing.forEach(notification => notification.remove());
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            notification.remove();
        }, 4000);
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Initial Data Loading
    async loadInitialData() {
        if (this.currentSection === 'charts') {
            await this.loadAllCharts();
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.bassMetricsApp = new BassMetricsApp();
});

// Make app globally accessible for debugging
window.BassMetricsApp = BassMetricsApp;
