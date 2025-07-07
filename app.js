class DubstepApp {
    constructor() {
        this.currentUser = null;
        this.authToken = localStorage.getItem('authToken');
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupAuth();
        this.setupForms();
        this.loadInitialData();
        
        if (this.authToken) {
            this.validateToken();
        }
    }

    setupNavigation() {
        const navBtns = document.querySelectorAll('.nav-btn');
        const sections = document.querySelectorAll('.section');

        navBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetSection = btn.dataset.section;
                
                navBtns.forEach(b => b.classList.remove('active'));
                sections.forEach(s => s.classList.remove('active'));
                
                btn.classList.add('active');
                document.getElementById(targetSection).classList.add('active');
                
                this.loadSectionData(targetSection);
            });
        });
    }

    setupAuth() {
        const loginForm = document.getElementById('loginFormElement');
        const registerForm = document.getElementById('registerFormElement');
        const showRegisterBtn = document.getElementById('showRegister');
        const showLoginBtn = document.getElementById('showLogin');
        const logoutBtn = document.getElementById('logoutBtn');

        loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        registerForm.addEventListener('submit', (e) => this.handleRegister(e));
        showRegisterBtn.addEventListener('click', () => this.toggleAuthForm('register'));
        showLoginBtn.addEventListener('click', () => this.toggleAuthForm('login'));
        logoutBtn.addEventListener('click', () => this.handleLogout());
    }

    setupForms() {
        const submitForm = document.getElementById('submitForm');
        const searchBtn = document.getElementById('searchBtn');
        const trackSearch = document.getElementById('trackSearch');
        const chartPeriod = document.getElementById('chartPeriod');
        const chartGenre = document.getElementById('chartGenre');

        submitForm.addEventListener('submit', (e) => this.handleTrackSubmit(e));
        searchBtn.addEventListener('click', () => this.handleTrackSearch());
        trackSearch.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleTrackSearch();
        });
        
        chartPeriod.addEventListener('change', () => this.loadCharts());
        chartGenre.addEventListener('change', () => this.loadCharts());
    }

    async validateToken() {
        try {
            const user = await API.validateToken(this.authToken);
            this.currentUser = user;
            this.updateAuthUI();
        } catch (error) {
            localStorage.removeItem('authToken');
            this.authToken = null;
            this.currentUser = null;
        }
    }

    async handleLogin(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await API.login(username, password);
            this.authToken = response.token;
            this.currentUser = response.user;
            
            localStorage.setItem('authToken', this.authToken);
            this.updateAuthUI();
            this.showNotification('Login successful!', 'success');
            
            document.getElementById('loginFormElement').reset();
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    async handleRegister(e) {
        e.preventDefault();
        
        const username = document.getElementById('regUsername').value;
        const email = document.getElementById('regEmail').value;
        const password = document.getElementById('regPassword').value;
        const confirmPassword = document.getElementById('regPasswordConfirm').value;

        if (password !== confirmPassword) {
            this.showNotification('Passwords do not match!', 'error');
            return;
        }

        try {
            await API.register(username, email, password);
            this.showNotification('Registration successful! Please login.', 'success');
            this.toggleAuthForm('login');
            document.getElementById('registerFormElement').reset();
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    handleLogout() {
        localStorage.removeItem('authToken');
        this.authToken = null;
        this.currentUser = null;
        this.updateAuthUI();
        this.showNotification('Logged out successfully!', 'success');
    }

    toggleAuthForm(form) {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        
        if (form === 'register') {
            loginForm.classList.add('hidden');
            registerForm.classList.remove('hidden');
        } else {
            registerForm.classList.add('hidden');
            loginForm.classList.remove('hidden');
        }
    }

    updateAuthUI() {
        const loginForm = document.getElementById('loginForm');
        const registerForm = document.getElementById('registerForm');
        const userProfile = document.getElementById('userProfile');
        
        if (this.currentUser) {
            loginForm.classList.add('hidden');
            registerForm.classList.add('hidden');
            userProfile.classList.remove('hidden');
            
            document.getElementById('profileUsername').textContent = this.currentUser.username;
            document.getElementById('votesCount').textContent = this.currentUser.votes_count || 0;
            document.getElementById('submissionsCount').textContent = this.currentUser.submissions_count || 0;
            document.getElementById('trustScore').textContent = this.currentUser.trust_score || 0;
        } else {
            userProfile.classList.add('hidden');
            loginForm.classList.remove('hidden');
            registerForm.classList.add('hidden');
        }
    }

    async loadSectionData(section) {
        switch (section) {
            case 'charts':
                await this.loadCharts();
                break;
            case 'vote':
                break;
            case 'submit':
                break;
            case 'profile':
                if (this.currentUser) {
                    await this.loadUserStats();
                }
                break;
        }
    }

    async loadInitialData() {
        await this.loadCharts();
    }

    async loadCharts() {
        const chartList = document.getElementById('chartList');
        const period = document.getElementById('chartPeriod').value;
        const genre = document.getElementById('chartGenre').value;
        
        chartList.innerHTML = '<div class="loading">Loading charts...</div>';
        
        try {
            const charts = await API.getCharts(period, genre);
            this.renderCharts(charts);
        } catch (error) {
            chartList.innerHTML = '<div class="info-message">Error loading charts. Please try again.</div>';
            console.error('Error loading charts:', error);
        }
    }

    renderCharts(tracks) {
        const chartList = document.getElementById('chartList');
        
        if (!tracks || tracks.length === 0) {
            chartList.innerHTML = '<div class="info-message">No tracks found for the selected criteria.</div>';
            return;
        }

        chartList.innerHTML = tracks.map((track, index) => `
            <div class="track-item">
                <div class="track-position">#${index + 1}</div>
                <div class="track-info">
                    <div class="track-title">${this.escapeHtml(track.title)}</div>
                    <div class="track-artist">${this.escapeHtml(track.artist)}</div>
                    <div class="track-meta">
                        <span>Genre: ${track.genre}</span>
                        <span>Votes: ${track.vote_count || 0}</span>
                        <span>Platforms: ${track.platform_count || 1}</span>
                    </div>
                </div>
                <div class="track-score">${track.score ? track.score.toFixed(1) : 'N/A'}</div>
            </div>
        `).join('');
    }

    async handleTrackSearch() {
        const query = document.getElementById('trackSearch').value.trim();
        const voteList = document.getElementById('voteList');
        
        if (!query) {
            voteList.innerHTML = '<div class="info-message">Please enter a search term.</div>';
            return;
        }

        voteList.innerHTML = '<div class="loading">Searching tracks...</div>';
        
        try {
            const tracks = await API.searchTracks(query);
            this.renderVotingTracks(tracks);
        } catch (error) {
            voteList.innerHTML = '<div class="info-message">Error searching tracks. Please try again.</div>';
            console.error('Error searching tracks:', error);
        }
    }

    renderVotingTracks(tracks) {
        const voteList = document.getElementById('voteList');
        
        if (!tracks || tracks.length === 0) {
            voteList.innerHTML = '<div class="info-message">No tracks found matching your search.</div>';
            return;
        }

        voteList.innerHTML = tracks.map(track => `
            <div class="track-item">
                <div class="track-info">
                    <div class="track-title">${this.escapeHtml(track.title)}</div>
                    <div class="track-artist">${this.escapeHtml(track.artist)}</div>
                    <div class="track-meta">
                        <span>Genre: ${track.genre}</span>
                        <span>Current Score: ${track.score ? track.score.toFixed(1) : 'N/A'}</span>
                    </div>
                    <div class="vote-section">
                        <input type="number" id="score-${track.id}" min="1" max="10" placeholder="Score (1-10)" ${!this.currentUser ? 'disabled' : ''}>
                        <button class="vote-btn" onclick="app.submitVote(${track.id})" ${!this.currentUser ? 'disabled' : ''}>
                            ${this.currentUser ? 'Vote' : 'Login to Vote'}
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    async submitVote(trackId) {
        if (!this.currentUser) {
            this.showNotification('Please login to vote!', 'error');
            return;
        }

        const scoreInput = document.getElementById(`score-${trackId}`);
        const score = parseInt(scoreInput.value);
        
        if (!score || score < 1 || score > 10) {
            this.showNotification('Please enter a valid score (1-10)!', 'error');
            return;
        }

        try {
            await API.submitVote(trackId, score, this.authToken);
            this.showNotification('Vote submitted successfully!', 'success');
            scoreInput.value = '';
            scoreInput.disabled = true;
            scoreInput.nextElementSibling.textContent = 'Voted';
            scoreInput.nextElementSibling.disabled = true;
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    async handleTrackSubmit(e) {
        e.preventDefault();
        
        if (!this.currentUser) {
            this.showNotification('Please login to submit tracks!', 'error');
            return;
        }

        const trackData = {
            url: document.getElementById('trackUrl').value,
            title: document.getElementById('trackTitle').value,
            artist: document.getElementById('trackArtist').value,
            genre: document.getElementById('trackGenre').value,
            description: document.getElementById('trackDescription').value
        };

        try {
            await API.submitTrack(trackData, this.authToken);
            this.showNotification('Track submitted successfully!', 'success');
            document.getElementById('submitForm').reset();
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    async loadUserStats() {
        if (!this.currentUser) return;
        
        try {
            const stats = await API.getUserStats(this.currentUser.id, this.authToken);
            document.getElementById('votesCount').textContent = stats.votes_count || 0;
            document.getElementById('submissionsCount').textContent = stats.submissions_count || 0;
            document.getElementById('trustScore').textContent = stats.trust_score || 0;
        } catch (error) {
            console.error('Error loading user stats:', error);
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.getElementById('notification');
        notification.textContent = message;
        notification.className = `notification ${type}`;
        notification.classList.remove('hidden');
        
        setTimeout(() => {
            notification.classList.add('hidden');
        }, 4000);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

const app = new DubstepApp();