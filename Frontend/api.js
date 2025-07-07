class API {
    static BASE_URL = 'http://localhost:5000';
    
    static async request(endpoint, options = {}) {
        const url = `${this.BASE_URL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        if (options.body && typeof options.body === 'object') {
            config.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || `HTTP error! status: ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    static async get(endpoint, token = null) {
        const headers = {};
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
        
        return this.request(endpoint, {
            method: 'GET',
            headers
        });
    }

    static async post(endpoint, data, token = null) {
        const headers = {};
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
        
        return this.request(endpoint, {
            method: 'POST',
            headers,
            body: data
        });
    }

    static async put(endpoint, data, token = null) {
        const headers = {};
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
        
        return this.request(endpoint, {
            method: 'PUT',
            headers,
            body: data
        });
    }

    static async delete(endpoint, token = null) {
        const headers = {};
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
        
        return this.request(endpoint, {
            method: 'DELETE',
            headers
        });
    }

    static async login(username, password) {
        return this.post('/auth/login', {
            username,
            password
        });
    }

    static async register(username, email, password) {
        return this.post('/auth/register', {
            username,
            email,
            password
        });
    }

    static async validateToken(token) {
        return this.get('/auth/validate', token);
    }

    static async getCharts(period = 'weekly', genre = 'all') {
        const params = new URLSearchParams();
        if (period !== 'weekly') params.append('period', period);
        if (genre !== 'all') params.append('genre', genre);
        
        const queryString = params.toString();
        const endpoint = `/charts${queryString ? `?${queryString}` : ''}`;
        
        return this.get(endpoint);
    }

    static async searchTracks(query) {
        const params = new URLSearchParams({ q: query });
        return this.get(`/tracks/search?${params}`);
    }

    static async getTrack(trackId) {
        return this.get(`/tracks/${trackId}`);
    }

    static async submitTrack(trackData, token) {
        return this.post('/tracks', trackData, token);
    }

    static async submitVote(trackId, score, token) {
        return this.post(`/tracks/${trackId}/vote`, {
            score
        }, token);
    }

    static async getTrackVotes(trackId, token) {
        return this.get(`/tracks/${trackId}/votes`, token);
    }

    static async submitComment(trackId, text, token) {
        return this.post(`/tracks/${trackId}/comments`, {
            text
        }, token);
    }

    static async getTrackComments(trackId) {
        return this.get(`/tracks/${trackId}/comments`);
    }

    static async getUserStats(userId, token) {
        return this.get(`/users/${userId}/stats`, token);
    }

    static async getUserProfile(userId, token) {
        return this.get(`/users/${userId}`, token);
    }

    static async updateUserProfile(userId, profileData, token) {
        return this.put(`/users/${userId}`, profileData, token);
    }

    static async getTrendingTracks(limit = 20) {
        return this.get(`/tracks/trending?limit=${limit}`);
    }

    static async getTopTracks(period = 'weekly', limit = 20) {
        const params = new URLSearchParams({
            period,
            limit: limit.toString()
        });
        return this.get(`/tracks/top?${params}`);
    }

    static async getRecentTracks(limit = 20) {
        return this.get(`/tracks/recent?limit=${limit}`);
    }

    static async getTracksByGenre(genre, limit = 20) {
        const params = new URLSearchParams({
            genre,
            limit: limit.toString()
        });
        return this.get(`/tracks/genre?${params}`);
    }

    static async getTracksByPlatform(platform, limit = 20) {
        const params = new URLSearchParams({
            platform,
            limit: limit.toString()
        });
        return this.get(`/tracks/platform?${params}`);
    }

    static async verifyTrack(trackId, token) {
        return this.post(`/tracks/${trackId}/verify`, {}, token);
    }

    static async reportTrack(trackId, reason, token) {
        return this.post(`/tracks/${trackId}/report`, {
            reason
        }, token);
    }

    static async getSystemStatus() {
        return this.get('/status');
    }

    static async getLeaderboard(type = 'voters', limit = 10) {
        const params = new URLSearchParams({
            type,
            limit: limit.toString()
        });
        return this.get(`/leaderboard?${params}`);
    }

    static async getWeeklyChart(week = null) {
        const params = new URLSearchParams();
        if (week) params.append('week', week);
        return this.get(`/charts/weekly?${params}`);
    }

    static async getMonthlyChart(month = null) {
        const params = new URLSearchParams();
        if (month) params.append('month', month);
        return this.get(`/charts/monthly?${params}`);
    }

    static async getArtistTracks(artist, limit = 20) {
        const params = new URLSearchParams({
            artist,
            limit: limit.toString()
        });
        return this.get(`/tracks/artist?${params}`);
    }

    static async getArtistStats(artist) {
        return this.get(`/artists/${encodeURIComponent(artist)}/stats`);
    }

    static async getGenreStats() {
        return this.get('/stats/genres');
    }

    static async getPlatformStats() {
        return this.get('/stats/platforms');
    }

    static async getVotingStats() {
        return this.get('/stats/voting');
    }

    static async searchArtists(query) {
        const params = new URLSearchParams({ q: query });
        return this.get(`/artists/search?${params}`);
    }

    static async followArtist(artistId, token) {
        return this.post(`/artists/${artistId}/follow`, {}, token);
    }

    static async unfollowArtist(artistId, token) {
        return this.delete(`/artists/${artistId}/follow`, token);
    }

    static async getFollowedArtists(token) {
        return this.get('/users/me/following', token);
    }

    static async getRecommendations(token, limit = 10) {
        const params = new URLSearchParams({
            limit: limit.toString()
        });
        return this.get(`/recommendations?${params}`, token);
    }

    static async getPersonalizedCharts(token, period = 'weekly') {
        const params = new URLSearchParams({ period });
        return this.get(`/charts/personalized?${params}`, token);
    }

    static async exportData(format = 'json', token) {
        const params = new URLSearchParams({ format });
        return this.get(`/export?${params}`, token);
    }

    static async importPlaylist(playlistData, token) {
        return this.post('/playlists/import', playlistData, token);
    }

    static async createPlaylist(name, description, token) {
        return this.post('/playlists', {
            name,
            description
        }, token);
    }

    static async addToPlaylist(playlistId, trackId, token) {
        return this.post(`/playlists/${playlistId}/tracks`, {
            track_id: trackId
        }, token);
    }

    static async removeFromPlaylist(playlistId, trackId, token) {
        return this.delete(`/playlists/${playlistId}/tracks/${trackId}`, token);
    }

    static async getUserPlaylists(token) {
        return this.get('/playlists', token);
    }

    static async getPlaylist(playlistId, token) {
        return this.get(`/playlists/${playlistId}`, token);
    }

    static async updatePlaylist(playlistId, data, token) {
        return this.put(`/playlists/${playlistId}`, data, token);
    }

    static async deletePlaylist(playlistId, token) {
        return this.delete(`/playlists/${playlistId}`, token);
    }

    static async sharePlaylist(playlistId, token) {
        return this.post(`/playlists/${playlistId}/share`, {}, token);
    }

    static async getSharedPlaylist(shareId) {
        return this.get(`/playlists/shared/${shareId}`);
    }

    static async getAnalytics(token, period = 'weekly') {
        const params = new URLSearchParams({ period });
        return this.get(`/analytics?${params}`, token);
    }

    static async getTrackAnalytics(trackId, token) {
        return this.get(`/tracks/${trackId}/analytics`, token);
    }
}

window.API = API;
