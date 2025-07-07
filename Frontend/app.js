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
        `).joi
