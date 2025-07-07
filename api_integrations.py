"""
API integrations for external platforms
"""

import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import time
from typing import Dict, List, Optional, Any
from config import Config
import logging

logger = logging.getLogger(__name__)

class SpotifyAPI:
    """Spotify Web API integration for track verification."""
    
    def __init__(self):
        self.client_id = Config.SPOTIFY_CLIENT_ID
        self.client_secret = Config.SPOTIFY_CLIENT_SECRET
        self.client = None
        
        if self.client_id and self.client_secret:
            try:
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
                self.client = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            except Exception as e:
                logger.error(f"Failed to initialize Spotify client: {e}")
    
    def search_track(self, artist: str, title: str) -> Optional[Dict]:
        """Search for a track by artist and title."""
        if not self.client:
            return None
            
        try:
            query = f"artist:{artist} track:{title}"
            results = self.client.search(q=query, type='track', limit=10)
            
            if results['tracks']['items']:
                # Return the best match (first result is usually most relevant)
                track = results['tracks']['items'][0]
                return {
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'url': track['external_urls']['spotify'],
                    'popularity': track['popularity'],
                    'duration_ms': track['duration_ms'],
                    'explicit': track['explicit'],
                    'preview_url': track['preview_url']
                }
        except Exception as e:
            logger.error(f"Spotify search error: {e}")
        
        return None
    
    def get_track_details(self, track_id: str) -> Optional[Dict]:
        """Get detailed track information by Spotify ID."""
        if not self.client:
            return None
            
        try:
            track = self.client.track(track_id)
            audio_features = self.client.audio_features([track_id])[0]
            
            return {
                'id': track['id'],
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'album': track['album']['name'],
                'url': track['external_urls']['spotify'],
                'popularity': track['popularity'],
                'duration_ms': track['duration_ms'],
                'explicit': track['explicit'],
                'preview_url': track['preview_url'],
                'release_date': track['album']['release_date'],
                'audio_features': audio_features
            }
        except Exception as e:
            logger.error(f"Spotify track details error: {e}")
        
        return None

class SoundCloudAPI:
    """SoundCloud API integration for track data."""
    
    def __init__(self):
        self.client_id = Config.SOUNDCLOUD_CLIENT_ID
        self.base_url = "https://api.soundcloud.com"
    
    def search_tracks(self, query: str, limit: int = 20) -> List[Dict]:
        """Search SoundCloud for tracks."""
        if not self.client_id:
            return []
            
        try:
            url = f"{self.base_url}/tracks"
            params = {
                'client_id': self.client_id,
                'q': query,
                'limit': limit,
                'linked_partitioning': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tracks = []
            
            for track in data.get('collection', []):
                tracks.append({
                    'id': track['id'],
                    'title': track['title'],
                    'artist': track['user']['username'],
                    'url': track['permalink_url'],
                    'duration': track['duration'],
                    'playback_count': track['playback_count'],
                    'likes_count': track['likes_count'],
                    'comment_count': track['comment_count'],
                    'created_at': track['created_at'],
                    'genre': track.get('genre', ''),
                    'description': track.get('description', ''),
                    'artwork_url': track.get('artwork_url', '')
                })
            
            return tracks
            
        except Exception as e:
            logger.error(f"SoundCloud search error: {e}")
            return []
    
    def get_track_by_url(self, url: str) -> Optional[Dict]:
        """Get track details from SoundCloud URL."""
        if not self.client_id:
            return None
            
        try:
            resolve_url = f"{self.base_url}/resolve"
            params = {
                'client_id': self.client_id,
                'url': url
            }
            
            response = requests.get(resolve_url, params=params, timeout=10)
            response.raise_for_status()
            
            track = response.json()
            
            return {
                'id': track['id'],
                'title': track['title'],
                'artist': track['user']['username'],
                'url': track['permalink_url'],
                'duration': track['duration'],
                'playback_count': track['playback_count'],
                'likes_count': track['likes_count'],
                'comment_count': track['comment_count'],
                'created_at': track['created_at'],
                'genre': track.get('genre', ''),
                'description': track.get('description', ''),
                'artwork_url': track.get('artwork_url', '')
            }
            
        except Exception as e:
            logger.error(f"SoundCloud URL resolve error: {e}")
            return None

class YouTubeAPI:
    """YouTube Data API integration."""
    
    def __init__(self):
        self.api_key = Config.YOUTUBE_API_KEY
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    def search_videos(self, query: str, limit: int = 20) -> List[Dict]:
        """Search YouTube for videos."""
        if not self.api_key:
            return []
            
        try:
            url = f"{self.base_url}/search"
            params = {
                'key': self.api_key,
                'q': query,
                'part': 'snippet',
                'type': 'video',
                'maxResults': limit,
                'videoCategoryId': '10'  # Music category
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            videos = []
            
            # Get video IDs for additional details
            video_ids = [item['id']['videoId'] for item in data.get('items', [])]
            
            if video_ids:
                video_details = self.get_video_details(video_ids)
                
                for item in data.get('items', []):
                    video_id = item['id']['videoId']
                    snippet = item['snippet']
                    details = video_details.get(video_id, {})
                    
                    videos.append({
                        'id': video_id,
                        'title': snippet['title'],
                        'channel': snippet['channelTitle'],
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'description': snippet['description'],
                        'published_at': snippet['publishedAt'],
                        'thumbnail': snippet['thumbnails']['default']['url'],
                        'view_count': details.get('viewCount', 0),
                        'like_count': details.get('likeCount', 0),
                        'comment_count': details.get('commentCount', 0),
                        'duration': details.get('duration', '')
                    })
            
            return videos
            
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
            return []
    
    def get_video_details(self, video_ids: List[str]) -> Dict[str, Dict]:
        """Get detailed statistics for videos."""
        if not self.api_key or not video_ids:
            return {}
            
        try:
            url = f"{self.base_url}/videos"
            params = {
                'key': self.api_key,
                'id': ','.join(video_ids),
                'part': 'statistics,contentDetails'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            details = {}
            
            for item in data.get('items', []):
                video_id = item['id']
                stats = item.get('statistics', {})
                content = item.get('contentDetails', {})
                
                details[video_id] = {
                    'viewCount': int(stats.get('viewCount', 0)),
                    'likeCount': int(stats.get('likeCount', 0)),
                    'commentCount': int(stats.get('commentCount', 0)),
                    'duration': content.get('duration', '')
                }
            
            return details
            
        except Exception as e:
            logger.error(f"YouTube video details error: {e}")
            return {}
    
    def get_video_by_url(self, url: str) -> Optional[Dict]:
        """Extract video details from YouTube URL."""
        # Extract video ID from URL
        video_id = self.extract_video_id(url)
        if not video_id:
            return None
            
        try:
            details = self.get_video_details([video_id])
            if not details:
                return None
                
            # Get basic video info
            url_info = f"{self.base_url}/videos"
            params = {
                'key': self.api_key,
                'id': video_id,
                'part': 'snippet'
            }
            
            response = requests.get(url_info, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('items'):
                return None
                
            item = data['items'][0]
            snippet = item['snippet']
            video_details = details[video_id]
            
            return {
                'id': video_id,
                'title': snippet['title'],
                'channel': snippet['channelTitle'],
                'url': url,
                'description': snippet['description'],
                'published_at': snippet['publishedAt'],
                'thumbnail': snippet['thumbnails']['default']['url'],
                'view_count': video_details.get('viewCount', 0),
                'like_count': video_details.get('likeCount', 0),
                'comment_count': video_details.get('commentCount', 0),
                'duration': video_details.get('duration', '')
            }
            
        except Exception as e:
            logger.error(f"YouTube URL details error: {e}")
            return None
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:v\/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

class TrackVerificationService:
    """Service for verifying and enriching track data across platforms."""
    
    def __init__(self):
        self.spotify = SpotifyAPI()
        self.soundcloud = SoundCloudAPI()
        self.youtube = YouTubeAPI()
    
    def verify_track_url(self, url: str) -> Optional[Dict]:
        """Verify a track URL and return platform-specific data."""
        url = url.lower()
        
        if 'spotify.com' in url:
            return self.verify_spotify_url(url)
        elif 'soundcloud.com' in url:
            return self.verify_soundcloud_url(url)
        elif 'youtube.com' in url or 'youtu.be' in url:
            return self.verify_youtube_url(url)
        else:
            return None
    
    def verify_spotify_url(self, url: str) -> Optional[Dict]:
        """Verify Spotify URL and extract track data."""
        # Extract track ID from Spotify URL
        track_id_match = re.search(r'track/([a-zA-Z0-9]+)', url)
        if not track_id_match:
            return None
            
        track_id = track_id_match.group(1)
        track_data = self.spotify.get_track_details(track_id)
        
        if track_data:
            return {
                'platform': 'spotify',
                'verified': True,
                'data': track_data
            }
        return None
    
    def verify_soundcloud_url(self, url: str) -> Optional[Dict]:
        """Verify SoundCloud URL and extract track data."""
        track_data = self.soundcloud.get_track_by_url(url)
        
        if track_data:
            return {
                'platform': 'soundcloud',
                'verified': True,
                'data': track_data
            }
        return None
    
    def verify_youtube_url(self, url: str) -> Optional[Dict]:
        """Verify YouTube URL and extract track data."""
        track_data = self.youtube.get_video_by_url(url)
        
        if track_data:
            return {
                'platform': 'youtube',
                'verified': True,
                'data': track_data
            }
        return None
    
    def cross_platform_search(self, artist: str, title: str) -> Dict[str, Any]:
        """Search for a track across all platforms."""
        results = {
            'spotify': None,
            'soundcloud': [],
            'youtube': []
        }
        
        # Search Spotify
        spotify_result = self.spotify.search_track(artist, title)
        if spotify_result:
            results['spotify'] = spotify_result
        
        # Search SoundCloud
        soundcloud_query = f"{artist} {title}"
        soundcloud_results = self.soundcloud.search_tracks(soundcloud_query, limit=5)
        results['soundcloud'] = soundcloud_results
        
        # Search YouTube
        youtube_query = f"{artist} {title}"
        youtube_results = self.youtube.search_videos(youtube_query, limit=5)
        results['youtube'] = youtube_results
        
        return results
    
    def enrich_track_data(self, track_data: Dict) -> Dict:
        """Enrich track data with cross-platform information."""
        artist = track_data.get('artist', '')
        title = track_data.get('title', '')
        
        if not artist or not title:
            return track_data
        
        # Get data from all platforms
        platform_data = self.cross_platform_search(artist, title)
        
        # Calculate aggregated metrics
        total_plays = 0
        total_likes = 0
        platform_count = 0
        
        for platform, data in platform_data.items():
            if data:
                if platform == 'spotify' and isinstance(data, dict):
                    platform_count += 1
                elif platform in ['soundcloud', 'youtube'] and isinstance(data, list) and data:
                    platform_count += 1
                    if platform == 'soundcloud':
                        total_plays += data[0].get('playback_count', 0)
                        total_likes += data[0].get('likes_count', 0)
                    elif platform == 'youtube':
                        total_plays += data[0].get('view_count', 0)
                        total_likes += data[0].get('like_count', 0)
        
        # Update track data
        track_data.update({
            'platform_data': platform_data,
            'platform_count': platform_count,
            'total_plays': total_plays,
            'total_likes': total_likes,
            'enriched_at': time.time()
        })
        
        return track_data