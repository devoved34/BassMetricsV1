from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import os
import hashlib
import json
from functools import wraps

# API integrations
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests

from config import Config
from models import db, User, Track, Vote, Comment, WeeklyChart, PlatformData, UserSession, APICache

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
CORS(app)
limiter = Limiter(
    app=app, 
    key_func=get_remote_address, 
    default_limits=["200 per day", "50 per hour"]
)

# Spotify API Client Setup
def get_spotify_client():
    """Initialize Spotify client with credentials from environment"""
    try:
        client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            print("Missing Spotify credentials")
            return None
            
        client_credentials_manager = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        return spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    except Exception as e:
        print(f"Spotify client error: {e}")
        return None

# Token validation decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(id=data['user_id']).first()
            if not current_user:
                return jsonify({'message': 'Token is invalid!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# HEALTH CHECK ENDPOINT
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway deployment"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'apis': {
            'spotify': bool(os.environ.get('SPOTIFY_CLIENT_ID') and os.environ.get('SPOTIFY_CLIENT_SECRET')),
            'youtube': bool(os.environ.get('YOUTUBE_API_KEY')),
            'database': True
        },
        'version': '1.0.0'
    }), 200

# AUTHENTICATION ENDPOINTS
@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("10 per hour")
def register():
    """Register a new user"""
    data = request.get_json()
    if not data or not all(data.get(k) for k in ['username', 'email', 'password']):
        return jsonify({'message': 'Missing required fields!'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists!'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already registered!'}), 400

    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password'])
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User created successfully!'}), 201

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("20 per hour")
def login():
    """Login user and return JWT token"""
    data = request.get_json()
    if not data or not all(data.get(k) for k in ['username', 'password']):
        return jsonify({'message': 'Missing credentials!'}), 400

    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'message': 'Invalid credentials!'}), 401

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    session_token = UserSession(
        token=token, 
        user_id=user.id, 
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.session.add(session_token)
    db.session.commit()

    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'votes_count': user.votes_count,
            'submissions_count': user.submissions_count,
            'trust_score': user.trust_score
        }
    })

@app.route('/api/auth/validate', methods=['GET'])
@token_required
def validate_token(current_user):
    """Validate JWT token and return user info"""
    return jsonify({
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'email': current_user.email,
            'votes_count': current_user.votes_count,
            'submissions_count': current_user.submissions_count,
            'trust_score': current_user.trust_score
        }
    })

# SPOTIFY API ENDPOINTS
@app.route('/api/spotify/trending', methods=['GET'])
def get_spotify_trending():
    """Get trending dubstep tracks from Spotify"""
    try:
        sp = get_spotify_client()
        if not sp:
            return jsonify({'error': 'Spotify API not configured'}), 500
        
        # Search for various dubstep-related terms
        search_queries = [
            'genre:dubstep year:2024',
            'dubstep 2024',
            'riddim 2024',
            'melodic dubstep'
        ]
        
        all_tracks = []
        seen_track_ids = set()
        
        for query in search_queries:
            try:
                results = sp.search(q=query, type='track', limit=10, market='US')
                
                for track in results['tracks']['items']:
                    if track['id'] in seen_track_ids:
                        continue
                    seen_track_ids.add(track['id'])
                    
                    # Get audio features for the track
                    try:
                        audio_features = sp.audio_features([track['id']])[0] if track['id'] else None
                    except:
                        audio_features = None
                    
                    track_data = {
                        'id': track['id'],
                        'title': track['name'],
                        'artist': track['artists'][0]['name'],
                        'album': track['album']['name'],
                        'popularity': track['popularity'],
                        'duration_ms': track['duration_ms'],
                        'preview_url': track['preview_url'],
                        'spotify_url': track['external_urls']['spotify'],
                        'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                        'release_date': track['album']['release_date'],
                        'explicit': track['explicit'],
                        'audio_features': {
                            'danceability': round(audio_features['danceability'] * 100, 1) if audio_features else 0,
                            'energy': round(audio_features['energy'] * 100, 1) if audio_features else 0,
                            'valence': round(audio_features['valence'] * 100, 1) if audio_features else 0,
                            'tempo': round(audio_features['tempo'], 1) if audio_features else 0,
                            'loudness': round(audio_features['loudness'], 1) if audio_features else 0
                        } if audio_features else None
                    }
                    all_tracks.append(track_data)
            except Exception as query_error:
                print(f"Error with query '{query}': {query_error}")
                continue
        
        # Sort by popularity and limit to top 20
        all_tracks.sort(key=lambda x: x['popularity'], reverse=True)
        tracks = all_tracks[:20]
        
        return jsonify({
            'tracks': tracks,
            'total': len(tracks),
            'source': 'spotify',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Spotify API error: {str(e)}'}), 500

@app.route('/api/youtube/trending', methods=['GET'])
def get_youtube_trending():
    """Get trending dubstep videos from YouTube"""
    try:
        youtube_api_key = os.environ.get('YOUTUBE_API_KEY')
        if not youtube_api_key:
            return jsonify({'error': 'YouTube API not configured'}), 500
        
        # Search for dubstep videos with multiple queries
        search_queries = [
            'dubstep 2024 -remix -mix',
            'riddim 2024 original',
            'melodic dubstep 2024',
            'bass music 2024'
        ]
        
        all_videos = []
        seen_video_ids = set()
        
        for query in search_queries:
            try:
                search_url = 'https://www.googleapis.com/youtube/v3/search'
                search_params = {
                    'key': youtube_api_key,
                    'q': query,
                    'part': 'snippet',
                    'type': 'video',
                    'maxResults': 8,
                    'order': 'relevance',
                    'videoCategoryId': '10',  # Music category
                    'publishedAfter': (datetime.utcnow() - timedelta(days=60)).isoformat() + 'Z'
                }
                
                search_response = requests.get(search_url, params=search_params, timeout=10)
                search_data = search_response.json()
                
                if 'items' not in search_data:
                    continue
                
                # Get video IDs for statistics
                video_ids = [item['id']['videoId'] for item in search_data['items'] 
                           if item['id']['videoId'] not in seen_video_ids]
                
                if not video_ids:
                    continue
                
                # Add to seen set
                seen_video_ids.update(video_ids)
                
                # Get video statistics
                stats_url = 'https://www.googleapis.com/youtube/v3/videos'
                stats_params = {
                    'key': youtube_api_key,
                    'id': ','.join(video_ids),
                    'part': 'statistics,contentDetails'
                }
                
                stats_response = requests.get(stats_url, params=stats_params, timeout=10)
                stats_data = stats_response.json()
                
                # Combine data
                stats_dict = {item['id']: item for item in stats_data.get('items', [])}
                
                for item in search_data['items']:
                    video_id = item['id']['videoId']
                    if video_id in seen_video_ids:
                        snippet = item['snippet']
                        stats = stats_dict.get(video_id, {}).get('statistics', {})
                        
                        video_data = {
                            'id': video_id,
                            'title': snippet['title'],
                            'channel': snippet['channelTitle'],
                            'description': snippet['description'][:200] + '...' if len(snippet['description']) > 200 else snippet['description'],
                            'published_at': snippet['publishedAt'],
                            'thumbnail_url': snippet['thumbnails']['medium']['url'],
                            'youtube_url': f'https://www.youtube.com/watch?v={video_id}',
                            'view_count': int(stats.get('viewCount', 0)),
                            'like_count': int(stats.get('likeCount', 0)),
                            'comment_count': int(stats.get('commentCount', 0)),
                            'duration': stats_dict.get(video_id, {}).get('contentDetails', {}).get('duration', '')
                        }
                        all_videos.append(video_data)
                        
            except Exception as query_error:
                print(f"Error with YouTube query '{query}': {query_error}")
                continue
        
        # Sort by view count and limit to top 20
        all_videos.sort(key=lambda x: x['view_count'], reverse=True)
        videos = all_videos[:20]
        
        return jsonify({
            'videos': videos,
            'total': len(videos),
            'source': 'youtube',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'YouTube API error: {str(e)}'}), 500

@app.route('/api/trending/combined', methods=['GET'])
def get_combined_trending():
    """Get combined trending data from Spotify and YouTube"""
    try:
        combined_data = {
            'spotify_tracks': [],
            'youtube_videos': [],
            'metrics': {
                'total_spotify_tracks': 0,
                'total_youtube_videos': 0,
                'avg_spotify_popularity': 0,
                'total_youtube_views': 0,
                'top_spotify_track': None,
                'top_youtube_video': None
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Get Spotify data
        try:
            sp = get_spotify_client()
            if sp:
                spotify_results = sp.search(q='genre:dubstep year:2024', type='track', limit=10, market='US')
                for track in spotify_results['tracks']['items']:
                    track_data = {
                        'title': track['name'],
                        'artist': track['artists'][0]['name'],
                        'popularity': track['popularity'],
                        'spotify_url': track['external_urls']['spotify'],
                        'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
                    }
                    combined_data['spotify_tracks'].append(track_data)
                
                combined_data['metrics']['total_spotify_tracks'] = len(combined_data['spotify_tracks'])
                if combined_data['spotify_tracks']:
                    combined_data['metrics']['avg_spotify_popularity'] = round(
                        sum(track['popularity'] for track in combined_data['spotify_tracks']) / 
                        len(combined_data['spotify_tracks']), 1
                    )
                    combined_data['metrics']['top_spotify_track'] = max(
                        combined_data['spotify_tracks'], 
                        key=lambda x: x['popularity']
                    )
        except Exception as e:
            print(f"Spotify error in combined: {e}")
        
        # Get YouTube data
        try:
            youtube_api_key = os.environ.get('YOUTUBE_API_KEY')
            if youtube_api_key:
                search_url = 'https://www.googleapis.com/youtube/v3/search'
                search_params = {
                    'key': youtube_api_key,
                    'q': 'dubstep 2024',
                    'part': 'snippet',
                    'type': 'video',
                    'maxResults': 10,
                    'order': 'viewCount',
                    'videoCategoryId': '10'
                }
                
                response = requests.get(search_url, params=search_params, timeout=10)
                data = response.json()
                
                if 'items' in data:
                    # Get video statistics
                    video_ids = [item['id']['videoId'] for item in data['items']]
                    stats_url = 'https://www.googleapis.com/youtube/v3/videos'
                    stats_params = {
                        'key': youtube_api_key,
                        'id': ','.join(video_ids),
                        'part': 'statistics'
                    }
                    
                    stats_response = requests.get(stats_url, params=stats_params, timeout=10)
                    stats_data = stats_response.json()
                    stats_dict = {item['id']: item['statistics'] for item in stats_data.get('items', [])}
                    
                    total_views = 0
                    for item in data['items']:
                        video_id = item['id']['videoId']
                        stats = stats_dict.get(video_id, {})
                        view_count = int(stats.get('viewCount', 0))
                        total_views += view_count
                        
                        video_data = {
                            'title': item['snippet']['title'],
                            'channel': item['snippet']['channelTitle'],
                            'published_at': item['snippet']['publishedAt'],
                            'youtube_url': f"https://www.youtube.com/watch?v={video_id}",
                            'view_count': view_count,
                            'thumbnail_url': item['snippet']['thumbnails']['medium']['url']
                        }
                        combined_data['youtube_videos'].append(video_data)
                    
                    combined_data['metrics']['total_youtube_videos'] = len(combined_data['youtube_videos'])
                    combined_data['metrics']['total_youtube_views'] = total_views
                    if combined_data['youtube_videos']:
                        combined_data['metrics']['top_youtube_video'] = max(
                            combined_data['youtube_videos'],
                            key=lambda x: x['view_count']
                        )
        except Exception as e:
            print(f"YouTube error in combined: {e}")
        
        return jsonify(combined_data)
        
    except Exception as e:
        return jsonify({'error': f'Combined API error: {str(e)}'}), 500

# ARTIST VERIFICATION ENDPOINT
@app.route('/api/verify/artist', methods=['GET'])
def verify_artist():
    """Verify artist on Spotify and get their stats"""
    artist_name = request.args.get('name')
    if not artist_name:
        return jsonify({'error': 'Artist name required'}), 400
    
    try:
        sp = get_spotify_client()
        if not sp:
            return jsonify({
                'verified': False,
                'error': 'Spotify API not configured'
            }), 500
        
        # Search for artist
        results = sp.search(q=f'artist:{artist_name}', type='artist', limit=1)
        
        if not results['artists']['items']:
            return jsonify({
                'verified': False,
                'message': 'Artist not found on Spotify',
                'requirements': {
                    'monthly_listeners': 10000,
                    'followers': 5000,
                    'account_age': 6
                }
            })
        
        artist = results['artists']['items'][0]
        followers = artist['followers']['total']
        popularity = artist['popularity']
        
        # Get artist's albums to estimate account age
        albums = sp.artist_albums(artist['id'], album_type='album,single', limit=50)
        account_age_months = 12  # Default
        if albums['items']:
            # Find oldest release
            oldest_date = min(
                album['release_date'] for album in albums['items'] 
                if album['release_date']
            )
            try:
                oldest = datetime.strptime(oldest_date, '%Y-%m-%d')
                account_age_months = max(1, int((datetime.now() - oldest).days / 30))
            except:
                pass
        
        # Calculate estimated monthly listeners based on popularity and followers
        estimated_monthly_listeners = int(followers * (popularity / 100) * 0.3)
        
        # Check verification criteria
        is_verified = (
            followers >= 5000 and 
            estimated_monthly_listeners >= 10000 and 
            account_age_months >= 6
        )
        
        return jsonify({
            'verified': is_verified,
            'platform': 'spotify',
            'artist_info': {
                'name': artist['name'],
                'id': artist['id'],
                'followers': followers,
                'popularity': popularity,
                'estimated_monthly_listeners': estimated_monthly_listeners,
                'account_age_months': account_age_months,
                'external_url': artist['external_urls']['spotify'],
                'image_url': artist['images'][0]['url'] if artist['images'] else None,
                'genres': artist['genres']
            },
            'requirements': {
                'monthly_listeners': 10000,
                'followers': 5000,
                'account_age': 6
            },
            'meets_requirements': {
                'followers': followers >= 5000,
                'monthly_listeners': estimated_monthly_listeners >= 10000,
                'account_age': account_age_months >= 6
            }
        })
        
    except Exception as e:
        return jsonify({
            'verified': False,
            'error': f'Spotify API error: {str(e)}'
        }), 500

# CHART ENDPOINTS
@app.route('/api/charts/algorithm', methods=['GET'])
def get_algorithm_charts():
    """Get algorithm-based charts (from Spotify)"""
    view = request.args.get('view', 'mainstream')
    limit = int(request.args.get('limit', 20))
    
    # For now, redirect to Spotify trending
    # In the future, this could combine Spotify + database tracks
    try:
        sp = get_spotify_client()
        if not sp:
            return jsonify({'error': 'Spotify API not configured'}), 500
        
        query = 'genre:dubstep year:2024' if view == 'mainstream' else 'dubstep OR riddim OR "bass music"'
        results = sp.search(q=query, type='track', limit=limit, market='US')
        
        tracks = []
        for i, track in enumerate(results['tracks']['items']):
            tracks.append({
                'id': track['id'],
                'rank': i + 1,
                'title': track['name'],
                'artist': track['artists'][0]['name'],
                'popularity': track['popularity'],
                'platforms': ['spotify'],
                'plays': f"{track['popularity'] * 10000:,}",
                'likes': f"{track['popularity'] * 500:,}",
                'score': track['popularity'],
                'trend': 'up' if track['popularity'] > 70 else 'stable',
                'spotify_url': track['external_urls']['spotify'],
                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
            })
        
        return jsonify({
            'tracks': tracks,
            'view': view,
            'total': len(tracks)
        })
        
    except Exception as e:
        return jsonify({'error': f'Algorithm charts error: {str(e)}'}), 500

@app.route('/api/charts/community', methods=['GET'])
def get_community_charts():
    """Get community-voted charts"""
    view = request.args.get('view', 'overall')
    limit = int(request.args.get('limit', 20))
    
    # Get tracks from database with votes
    query = Track.query.filter(Track.vote_count > 0).order_by(Track.score.desc()).limit(limit)
    tracks = query.all()
    
    if not tracks:
        # Return mock data if no tracks in database yet
        mock_tracks = []
        for i in range(min(limit, 10)):
            mock_tracks.append({
                'id': f'mock-{i}',
                'rank': i + 1,
                'title': f'Community Track {i + 1}',
                'artist': f'Community Artist {i + 1}',
                'platforms': ['spotify', 'youtube'],
                'dropQuality': round(7 + (i * 0.2), 1),
                'production': round(8 + (i * 0.1), 1),
                'bassQuality': round(7.5 + (i * 0.15), 1),
                'overall_score': round(7.5 + (i * 0.12), 1),
                'voteCount': 100 - (i * 5),
                'trend': 'up' if i < 3 else 'stable'
            })
        
        return jsonify({
            'tracks': mock_tracks,
            'view': view,
            'total': len(mock_tracks)
        })
    
    # Return real database tracks
    result = []
    for i, track in enumerate(tracks):
        result.append({
            'id': track.id,
            'rank': i + 1,
            'title': track.title,
            'artist': track.artist,
            'overall_score': track.score,
            'voteCount': track.vote_count,
            'platforms': ['spotify', 'youtube'],  # Default for now
            'trend': 'up' if track.score > 7.5 else 'stable'
        })
    
    return jsonify({
        'tracks': result,
        'view': view,
        'total': len(result)
    })

@app.route('/api/charts/underground', methods=['GET'])
def get_underground_charts():
    """Get underground tracks"""
    limit = int(request.args.get('limit', 10))
    
    # Mock underground data for now
    tracks = []
    for i in range(limit):
        tracks.append({
            'id': f'underground-{i}',
            'rank': i + 1,
            'title': f'Underground Track {i + 1}',
            'artist': f'Underground Artist {i + 1}',
            'platforms': ['soundcloud', 'youtube'],
            'plays': f'{20000 + (i * 1000):,}',
            'likes': f'{500 + (i * 50):,}',
            'score': 85 - i,
            'trend': 'up'
        })
    
    return jsonify({
        'tracks': tracks,
        'total': len(tracks)
    })

@app.route('/api/charts/rising', methods=['GET'])
def get_rising_charts():
    """Get rising tracks"""
    limit = int(request.args.get('limit', 10))
    
    # Mock rising data for now
    tracks = []
    for i in range(limit):
        tracks.append({
            'id': f'rising-{i}',
            'rank': i + 1,
            'title': f'Rising Track {i + 1}',
            'artist': f'Rising Artist {i + 1}',
            'platforms': ['soundcloud'],
            'plays': f'{10000 + (i * 500):,}',
            'likes': f'{200 + (i * 25):,}',
            'score': 90 - i,
            'trend': 'up'
        })
    
    return jsonify({
        'tracks': tracks,
        'total': len(tracks)
    })

# TRACK MANAGEMENT ENDPOINTS
@app.route('/api/tracks/search', methods=['GET'])
def search_tracks():
    """Search tracks in database"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    limit = int(request.args.get('limit', 20))
    tracks = Track.query.filter(
        (Track.title.ilike(f'%{query}%')) | (Track.artist.ilike(f'%{query}%'))
    ).order_by(Track.score.desc()).limit(limit).all()
    
    result = []
    for track in tracks:
        result.append({
            'id': track.id,
            'title': track.title,
            'artist': track.artist,
            'genre': track.genre,
            'score': track.score,
            'vote_count': track.vote_count,
            'created_at': track.created_at.isoformat()
        })
    
    return jsonify(result)

@app.route('/api/tracks', methods=['POST'])
@token_required
@limiter.limit("5 per hour")
def submit_track(current_user):
    """Submit a new track"""
    data = request.get_json()
    if not all(k in data for k in ['url', 'title', 'artist', 'genre']):
        return jsonify({'message': 'Missing required fields!'}), 400

    if Track.query.filter_by(title=data['title'], artist=data['artist']).first():
        return jsonify({'message': 'Track already exists!'}), 400

    track = Track(
        title=data['title'],
        artist=data['artist'],
        genre=data['genre'],
        description=data.get('description', ''),
        submitted_by=current_user.id
    )
    db.session.add(track)
    db.session.flush()

    platform_data = PlatformData(
        track_id=track.id,
        platform='submitted',
        url=data['url'],
        external_id=hashlib.md5(data['url'].encode()).hexdigest()
    )
    db.session.add(platform_data)

    current_user.submissions_count += 1
    current_user.trust_score += 2
    db.session.commit()

    return jsonify({'message': 'Track submitted!', 'track_id': track.id}), 201

# VOTING ENDPOINTS
@app.route('/api/voting/tracks', methods=['GET'])
def get_voting_tracks():
    """Get tracks available for voting"""
    limit = int(request.args.get('limit', 10))
    
    # Get tracks from database, or return mock data
    tracks = Track.query.order_by(Track.created_at.desc()).limit(limit).all()
    
    if not tracks:
        # Return mock voting tracks
        mock_tracks = []
        for i in range(5):
            mock_tracks.append({
                'id': f'vote-{i}',
                'title': f'Vote Track {i + 1}',
                'artist': f'Vote Artist {i + 1}',
                'platforms': ['spotify', 'youtube'],
                'spotify_url': 'https://open.spotify.com/track/example',
                'youtube_url': 'https://www.youtube.com/watch?v=example'
            })
        return jsonify(mock_tracks)
    
    # Return real tracks
    result = []
    for track in tracks:
        result.append({
            'id': track.id,
            'title': track.title,
            'artist': track.artist,
            'platforms': ['spotify', 'youtube'],  # Default platforms
            'spotify_url': 'https://open.spotify.com/search/' + track.artist + ' ' + track.title,
            'youtube_url': 'https://www.youtube.com/results?search_query=' + track.artist + ' ' + track.title
        })
    
    return jsonify(result)

@app.route('/api/voting/vote', methods=['POST'])
@token_required
@limiter.limit("50 per hour")
def vote_track(current_user):
    """Submit a vote for a track"""
    data = request.get_json()
    track_id = data.get('track_id')
    scores = data.get('scores', {})
    
    if not track_id:
        return jsonify({'message': 'Track ID required!'}), 400
    
    # For mock tracks, just return success
    if str(track_id).startswith('vote-'):
        return jsonify({'message': 'Vote submitted successfully!', 'track_id': track_id})
    
    # Handle real database tracks
    track = Track.query.get(track_id)
    if not track:
        return jsonify({'message': 'Track not found!'}), 404
    
    # Check if user already voted
    existing_vote = Vote.query.filter_by(user_id=current_user.id, track_id=track_id).first()
    if existing_vote:
        return jsonify({'message': 'Already voted on this track!'}), 400
    
    # Calculate overall score from component scores
    component_scores = scores
    overall_score = sum(component_scores.values()) / len(component_scores) if component_scores else 5
    
    vote = Vote(
        user_id=current_user.id,
        track_id=track_id,
        score=int(overall_score),
        drop_quality=component_scores.get('dropQuality', 5),
        production=component_scores.get('production', 5),
        bass_low_end=component_scores.get('bassQuality', 5),
        originality=component_scores.get('originality', 5),
        vote_type='advanced'
    )
    
    db.session.add(vote)
    
    # Update track stats
    track.vote_count += 1
    track.total_score += overall_score
    track.score = track.total_score / track.vote_count
    
    # Update user stats
    current_user.votes_count += 1
    current_user.trust_score += 1
    
    db.session.commit()
    
    return jsonify({
        'message': 'Vote submitted successfully!',
        'new_score': track.score,
        'vote_count': track.vote_count
    })

# COMMENT ENDPOINTS
@app.route('/api/tracks/<int:track_id>/comments', methods=['POST'])
@token_required
@limiter.limit("20 per hour")
def add_comment(current_user, track_id):
    """Add a comment to a track"""
    data = request.get_json()
    text = data.get('text', '').strip()
    
    if len(text) < 5:
        return jsonify({'message': 'Comment must be at least 5 characters!'}), 400

    comment = Comment(
        user_id=current_user.id,
        track_id=track_id,
        text=text,
        content=text
    )
    db.session.add(comment)
    current_user.trust_score += 1
    db.session.commit()
    
    return jsonify({
        'message': 'Comment added successfully!',
        'comment_id': comment.id
    }), 201

@app.route('/api/tracks/<int:track_id>/comments', methods=['GET'])
def get_comments(track_id):
    """Get comments for a track"""
    comments = Comment.query.filter_by(track_id=track_id).order_by(Comment.created_at.desc()).all()
    
    result = []
    for comment in comments:
        result.append({
            'id': comment.id,
            'text': comment.text,
            'username': comment.user.username,
            'created_at': comment.created_at.isoformat(),
            'sentiment_score': comment.sentiment_score
        })
    
    return jsonify(result)

# USER STATS ENDPOINTS
@app.route('/api/users/<int:user_id>/stats', methods=['GET'])
@token_required
def get_user_stats(current_user, user_id):
    """Get user statistics"""
    if current_user.id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    return jsonify({
        'votes_count': current_user.votes_count,
        'submissions_count': current_user.submissions_count,
        'trust_score': current_user.trust_score,
        'comments_count': Comment.query.filter_by(user_id=user_id).count(),
        'member_since': current_user.created_at.isoformat()
    })

# TRENDING AND METRICS ENDPOINTS
@app.route('/api/tracks/trending', methods=['GET'])
def get_trending_tracks():
    """Get trending tracks from last 24 hours"""
    limit = int(request.args.get('limit', 20))
    
    cache_key = f"trending_{limit}"
    cached = APICache.get_cached(cache_key)
    if cached:
        return jsonify(cached)
    
    last_24h = datetime.utcnow() - timedelta(hours=24)
    tracks = Track.query.filter(
        Track.created_at >= last_24h
    ).order_by(Track.score.desc()).limit(limit).all()
    
    result = []
    for track in tracks:
        result.append({
            'id': track.id,
            'title': track.title,
            'artist': track.artist,
            'genre': track.genre,
            'score': track.score,
            'vote_count': track.vote_count,
            'created_at': track.created_at.isoformat()
        })
    
    APICache.set_cached(cache_key, result, 300)
    return jsonify(result)

@app.route('/api/tracks/top', methods=['GET'])
def get_top_tracks():
    """Get top tracks by period"""
    period = request.args.get('period', 'weekly')
    limit = int(request.args.get('limit', 20))
    
    cache_key = f"top_{period}_{limit}"
    cached = APICache.get_cached(cache_key)
    if cached:
        return jsonify(cached)
    
    query = Track.query
    
    if period == 'weekly':
        week_ago = datetime.utcnow() - timedelta(days=7)
        query = query.filter(Track.created_at >= week_ago)
    elif period == 'monthly':
        month_ago = datetime.utcnow() - timedelta(days=30)
        query = query.filter(Track.created_at >= month_ago)
    
    tracks = query.order_by(Track.score.desc()).limit(limit).all()
    
    result = []
    for track in tracks:
        result.append({
            'id': track.id,
            'title': track.title,
            'artist': track.artist,
            'genre': track.genre,
            'score': track.score,
            'vote_count': track.vote_count,
            'created_at': track.created_at.isoformat()
        })
    
    APICache.set_cached(cache_key, result, 300)
    return jsonify(result)

# METRICS ENDPOINT FOR DASHBOARD
@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Get platform metrics for dashboard"""
    try:
        # Get basic database stats
        total_tracks = Track.query.count()
        total_users = User.query.count()
        total_votes = Vote.query.count()
        
        # Get top track
        top_track = Track.query.order_by(Track.score.desc()).first()
        
        # Calculate average rating
        avg_rating = 0
        if total_votes > 0:
            total_score = db.session.query(db.func.sum(Vote.score)).scalar() or 0
            avg_rating = round(total_score / total_votes, 1)
        
        # Get recent activity
        recent_tracks = Track.query.filter(
            Track.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        return jsonify({
            'total_tracks': total_tracks,
            'total_users': total_users,
            'total_votes': total_votes,
            'avg_rating': avg_rating,
            'most_voted_track': top_track.title + ' - ' + top_track.artist if top_track else 'No tracks yet',
            'recent_activity': {
                'tracks_this_week': recent_tracks,
                'votes_this_week': Vote.query.filter(
                    Vote.created_at >= datetime.utcnow() - timedelta(days=7)
                ).count()
            },
            'top_rated_by_component': {
                'drop_quality': 8.5,  # Mock data - would calculate from real votes
                'production': 8.3,
                'bass': 8.8,
                'originality': 7.9
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': f'Metrics error: {str(e)}'}), 500

# SYSTEM STATUS ENDPOINTS
@app.route('/api/status', methods=['GET'])
def status():
    """Get system status"""
    return jsonify({
        'status': 'online',
        'version': '1.0.0',
        'tracks_count': Track.query.count(),
        'users_count': User.query.count(),
        'votes_count': Vote.query.count(),
        'apis': {
            'spotify': bool(os.environ.get('SPOTIFY_CLIENT_ID')),
            'youtube': bool(os.environ.get('YOUTUBE_API_KEY')),
            'database': True
        },
        'timestamp': datetime.utcnow().isoformat()
    })

# ERROR HANDLERS
@app.errorhandler(404)
def not_found(e):
    return jsonify({'message': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return jsonify({'message': 'Internal server error'}), 500

@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({'message': 'Rate limit exceeded'}), 429

# INITIALIZE DATABASE
@app.before_first_request
def create_tables():
    """Create database tables on first request"""
    try:
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")

# MAIN APPLICATION
if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database initialized successfully")
            print(f"✅ Spotify API: {'Configured' if os.environ.get('SPOTIFY_CLIENT_ID') else 'Not configured'}")
            print(f"✅ YouTube API: {'Configured' if os.environ.get('YOUTUBE_API_KEY') else 'Not configured'}")
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
    
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    
    print(f"🚀 Starting BassMetrics API on port {port}")
    app.run(debug=debug, host='0.0.0.0', port=port)
