/**
 * BassMetrics API Integration
 * Handles all API calls to backend services
 */

class APIManager {
    constructor() {
        // Updated to use your Railway API URL
        this.baseURL = 'https://bassmetricsv1-production.up.railway.app/api';
        this.timeout = 10000; // 10 second timeout
        this.retryAttempts = 3;
        
        // API endpoints
        this.endpoints = {
            // New Railway API endpoints
            health: '/health',
            spotifyTrending: '/spotify/trending',
            youtubeTrending: '/youtube/trending',
            combinedTrending: '/trending/combined',
            metrics: '/metrics',
            
            // Chart endpoints
            algorithmCharts: '/charts/algorithm',
            communityCharts: '/charts/community', 
            undergroundCharts: '/charts/underground',
            risingCharts: '/charts/rising',
            
            // Verification endpoints
            verifyArtist: '/verify/artist',
            
            // Submission endpoints
            submitTrack: '/submit/track',
            
            // Voting endpoints
            votingTracks: '/voting/tracks',
            submitVote: '/voting/vote',
            
            // User endpoints
            login: '/auth/login',
            register: '/auth/register',
            profile: '/auth/profile',
            
            // Platform endpoints
            spotifySearch: '/platforms/spotify/search',
            soundcloudSearch: '/platforms/soundcloud/search',
            youtubeSearch: '/platforms/youtube/search'
        };
    }

    // Generic API request handler with retry logic
    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.timeout);
                
                const response = await fetch(url, {
                    ...config,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                return data;
                
            } catch (error) {
                console.warn(`API request attempt ${attempt} failed:`, error.message);
                
                if (attempt === this.retryAttempts) {
                    throw new Error(`API request failed after ${this.retryAttempts} attempts: ${error.message}`);
                }
                
                // Exponential backoff
                await this.delay(Math.pow(2, attempt) * 1000);
            }
        }
    }

    // NEW RAILWAY API METHODS
    async getHealth() {
        try {
            return await this.makeRequest(this.endpoints.health);
        } catch (error) {
            console.error('Health check failed:', error);
            throw error;
        }
    }

    async getSpotifyTrending() {
        try {
            const response = await this.makeRequest(this.endpoints.spotifyTrending);
            return response;
        } catch (error) {
            console.error('Failed to fetch Spotify trending:', error);
            throw error;
        }
    }

    async getYouTubeTrending() {
        try {
            const response = await this.makeRequest(this.endpoints.youtubeTrending);
            return response;
        } catch (error) {
            console.error('Failed to fetch YouTube trending:', error);
            throw error;
        }
    }

    async getCombinedTrending() {
        try {
            const response = await this.makeRequest(this.endpoints.combinedTrending);
            return response;
        } catch (error) {
            console.error('Failed to fetch combined trending:', error);
            throw error;
        }
    }

    async getMetrics() {
        try {
            const response = await this.makeRequest(this.endpoints.metrics);
            return response;
        } catch (error) {
            console.error('Failed to fetch metrics:', error);
            throw error;
        }
    }

    // Authentication token management
    getAuthToken() {
        return localStorage.getItem('bassMetricsToken');
    }

    setAuthToken(token) {
        localStorage.setItem('bassMetricsToken', token);
    }

    clearAuthToken() {
        localStorage.removeItem('bassMetricsToken');
    }

    getAuthHeaders() {
        const token = this.getAuthToken();
        return token ? { 'Authorization': `Bearer ${token}` } : {};
    }

    // VERIFICATION API METHODS (Updated to use Railway endpoint)
    async verifyArtist(artistName, platform = 'spotify') {
        try {
            const response = await this.makeRequest(
                `${this.endpoints.verifyArtist}?name=${encodeURIComponent(artistName)}&platform=${platform}`
            );
            return response;
        } catch (error) {
            console.error('Artist verification failed:', error);
            throw error;
        }
    }

    // UTILITY METHODS
    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }
}

// Create global instance
const apiManager = new APIManager();

// Simple test function
window.testAPI = async function() {
    console.log('Testing BassMetrics API...');
    try {
        console.log('API Manager:', apiManager);
        
        const health = await apiManager.getHealth();
        console.log('✓ Health check:', health);
        
        const spotify = await apiManager.getSpotifyTrending();
        console.log('✓ Spotify trending:', spotify);
        
        alert('API is working! Check console for details.');
        return spotify;
    } catch (error) {
        console.error('✗ API test failed:', error);
        alert('API test failed: ' + error.message);
        return null;
    }
};

console.log('BassMetrics API Manager loaded successfully');
