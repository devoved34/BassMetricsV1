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

    // CHART API METHODS
    async getAlgorithmCharts(view = 'mainstream', limit = 20) {
        try {
            return await this.makeRequest(
                `${this.endpoints.algorithmCharts}?view=${view}&limit=${limit}`
            );
        } catch (error) {
            console.error('Failed to fetch algorithm charts:', error);
            throw error;
        }
    }

    async getCommunityCharts(view = 'overall', limit = 20) {
        try {
            return await this.makeRequest(
                `${this.endpoints.communityCharts}?view=${view}&limit=${limit}`
            );
        } catch (error) {
            console.error('Failed to fetch community charts:', error);
            throw error;
        }
    }

    async getUndergroundTracks(limit = 10) {
        try {
            return await this.makeRequest(
                `${this.endpoints.undergroundCharts}?limit=${limit}`
            );
        } catch (error) {
            console.error('Failed to fetch underground tracks:', error);
            throw error;
        }
    }

    async getRisingTracks(limit = 10) {
        try {
            return await this.makeRequest(
                `${this.endpoints.risingCharts}?limit=${limit}`
            );
        } catch (error) {
            console.error('Failed to fetch rising tracks:', error);
            throw error;
        }
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

    // SUBMISSION API METHODS
    async submitTrack(trackData) {
        try {
            return await this.makeRequest(this.endpoints.submitTrack, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify(trackData)
            });
        } catch (error) {
            console.error('Track submission failed:', error);
            throw error;
        }
    }

    // VOTING API METHODS
    async getTracksForVoting(limit = 10, genre = null) {
        try {
            let url = `${this.endpoints.votingTracks}?limit=${limit}`;
            if (genre) {
                url += `&genre=${genre}`;
            }
            return await this.makeRequest(url);
        } catch (error) {
            console.error('Failed to fetch voting tracks:', error);
            throw error;
        }
    }

    async submitVote(trackId, scores) {
        try {
            return await this.makeRequest(this.endpoints.submitVote, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify({
                    track_id: trackId,
                    scores: scores
                })
            });
        } catch (error) {
            console.error('Vote submission failed:', error);
            throw error;
        }
    }

    // USER AUTHENTICATION API METHODS
    async login(credentials) {
        try {
            const response = await this.makeRequest(this.endpoints.login, {
                method: 'POST',
                body: JSON.stringify(credentials)
            });
            
            if (response.token) {
                this.setAuthToken(response.token);
            }
            
            return response;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    }

    async register(userData) {
        try {
            const response = await this.makeRequest(this.endpoints.register, {
                method: 'POST',
                body: JSON.stringify(userData)
            });
            
            if (response.token) {
                this.setAuthToken(response.token);
            }
            
            return response;
        } catch (error) {
            console.error('Registration failed:', error);
            throw error;
        }
    }

    async getUserProfile() {
        try {
            return await this.makeRequest(this.endpoints.profile, {
                headers: this.getAuthHeaders()
            });
        } catch (error) {
            console.error('Failed to fetch user profile:', error);
            throw error;
        }
    }

    async logout() {
        this.clearAuthToken();
        return { success: true };
    }

    // PLATFORM INTEGRATION API METHODS
    async searchSpotify(query) {
        try {
            return await this.makeRequest(
                `${this.endpoints.spotifySearch}?q=${encodeURIComponent(query)}`
            );
        } catch (error) {
            console.error('Spotify search failed:', error);
            throw error;
        }
    }

    async searchSoundCloud(query) {
        try {
            return await this.makeRequest(
                `${this.endpoints.soundcloudSearch}?q=${encodeURIComponent(query)}`
            );
        } catch (error) {
            console.error('SoundCloud search failed:', error);
            throw error;
        }
    }

    async searchYouTube(query) {
        try {
            return await this.makeRequest(
                `${this.endpoints.youtubeSearch}?q=${encodeURIComponent(query)}`
            );
        } catch (error) {
            console.error('YouTube search failed:', error);
            throw error;
        }
    }

    // EMBEDDED PLAYER HELPERS
    getSoundCloudEmbed(trackUrl) {
        if (!trackUrl) return null;
        
        try {
            // Extract track info from SoundCloud URL
            const trackId = this.extractSoundCloudId(trackUrl);
            if (!trackId) return null;
            
            return `https://w.soundcloud.com/player/?url=${encodeURIComponent(trackUrl)}&color=%23ff0000&auto_play=false&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true&visual=true`;
        } catch (error) {
            console.error('Failed to generate SoundCloud embed:', error);
            return null;
        }
    }

    getYouTubeEmbed(videoUrl) {
        if (!videoUrl) return null;
        
        try {
            const videoId = this.extractYouTubeId(videoUrl);
            if (!videoId) return null;
            
            return `https://www.youtube.com/embed/${videoId}?autoplay=0&controls=1&rel=0`;
        } catch (error) {
            console.error('Failed to generate YouTube embed:', error);
            return null;
        }
    }

    getSpotifyEmbed(trackUrl) {
        if (!trackUrl) return null;
        
        try {
            // Convert Spotify URL to embed format
            const trackId = this.extractSpotifyId(trackUrl);
            if (!trackId) return null;
            
            return `https://open.spotify.com/embed/track/${trackId}`;
        } catch (error) {
            console.error('Failed to generate Spotify embed:', error);
            return null;
        }
    }

    // URL EXTRACTION HELPERS
    extractSoundCloudId(url) {
        const patterns = [
            /soundcloud\.com\/([^\/]+)\/([^\/\?]+)/,
            /api\.soundcloud\.com\/tracks\/(\d+)/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[match.length - 1];
        }
        
        return null;
    }

    extractYouTubeId(url) {
        const patterns = [
            /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/,
            /youtube\.com\/embed\/([^&\n?#]+)/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match && match[1]) return match[1];
        }
        
        return null;
    }

    extractSpotifyId(url) {
        const patterns = [
            /spotify\.com\/track\/([^&\n?#]+)/,
            /spotify:track:([^&\n?#]+)/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match && match[1]) return match[1];
        }
        
        return null;
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

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIManager;
}

// Example usage in your frontend:
/*
// Test the API connection
apiManager.getHealth().then(data => {
    console.log('API Health:', data);
});

// Get Spotify trending tracks
apiManager.getSpotifyTrending().then(data => {
    console.log('Spotify Trending:', data);
    // Display tracks in your UI
});

// Get YouTube trending
apiManager.getYouTubeTrending().then(data => {
    console.log('YouTube Trending:', data);
});

// Get combined trending from both platforms
apiManager.getCombinedTrending().then(data => {
    console.log('Combined Trending:', data);
});

// Verify an artist
apiManager.verifyArtist('Skrillex').then(data => {
    console.log('Artist Verification:', data);
});

// Get platform metrics
apiManager.getMetrics().then(data => {
    console.log('Platform Metrics:', data);
});
*/
