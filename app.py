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

from config import Config
from models import db, User, Track, Vote, Comment, WeeklyChart, PlatformData, UserSession, APICache

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
CORS(app)

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

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

@app.route('/auth/register', methods=['POST'])
@limiter.limit("10 per hour")
def register():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
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

@app.route('/auth/login', methods=['POST'])
@limiter.limit("20 per hour")
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing username or password!'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'message': 'Invalid username or password!'}), 401
    
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

@app.route('/auth/validate', methods=['GET'])
@token_required
def validate_token(current_user):
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

@app.route('/charts', methods=['GET'])
def get_charts():
    period = request.args.get('period', 'weekly')
    genre = request.args.get('genre', 'all')
    limit = int(request.args.get('limit', 20))
    
    cache_key = f"charts_{period}_{genre}_{limit}"
    cached_result = APICache.get_cached(cache_key)
    if cached_result:
        return jsonify(cached_result)
    
    query = Track.query
    
    if genre != 'all':
        query = query.filter(Track.genre == genre)
    
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
            'platform_count': len(track.platform_data),
            'created_at': track.created_at.isoformat()
        })
    
    APICache.set_cached(cache_key, result, 300)
    return jsonify(result)

@app.route('/tracks/search', methods=['GET'])
def search_tracks():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    limit = int(request.args.get('limit', 20))
    
    tracks = Track.query.filter(
        (Track.title.ilike(f'%{query}%')) |
        (Track.artist.ilike(f'%{query}%'))
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

@app.route('/tracks', methods=['POST'])
@token_required
@limiter.limit("5 per hour")
def submit_track(current_user):
    data = request.get_json()
    
    required_fields = ['url', 'title', 'artist', 'genre']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Missing required fields!'}), 400
    
    existing_track = Track.query.filter_by(
        title=data['title'],
        artist=data['artist']
    ).first()
    
    if existing_track:
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
    
    return jsonify({
        'message': 'Track submitted successfully!',
        'track_id': track.id
    }), 201

@app.route('/tracks/<int:track_id>/vote', methods=['POST'])
@token_required
@limiter.limit("50 per hour")
def vote_track(current_user, track_id):
    data = request.get_json()
    
    if not data or 'score' not in data:
        return jsonify({'message': 'Score is required!'}), 400
    
    score = data['score']
    if not isinstance(score, int) or score < 1 or score > 10:
        return jsonify({'message': 'Score must be between 1 and 10!'}), 400
    
    track = Track.query.get_or_404(track_id)
    
    existing_vote = Vote.query.filter_by(
        user_id=current_user.id,
        track_id=track_id
    ).first()
    
    if existing_vote:
        return jsonify({'message': 'You have already voted on this track!'}), 400
    
    vote = Vote(
        user_id=current_user.id,
        track_id=track_id,
        score=score
    )
    
    db.session.add(vote)
    
    track.vote_count += 1
    track.total_score += score
    track.score = track.total_score / track.vote_count
    
    current_user.votes_count += 1
    current_user.trust_score += 1
    
    db.session.commit()
    
    return jsonify({
        'message': 'Vote submitted successfully!',
        'new_score': track.score
    })

@app.route('/tracks/<int:track_id>/comments', methods=['POST'])
@token_required
@limiter.limit("20 per hour")
def add_comment(current_user, track_id):
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'message': 'Comment text is required!'}), 400
    
    text = data['text'].strip()
    if not text or len(text) < 5:
        return jsonify({'message': 'Comment must be at least 5 characters!'}), 400
    
    track = Track.query.get_or_404(track_id)
    
    comment = Comment(
        user_id=current_user.id,
        track_id=track_id,
        text=text
    )
    
    db.session.add(comment)
    current_user.trust_score += 1
    db.session.commit()
    
    return jsonify({
        'message': 'Comment added successfully!',
        'comment_id': comment.id
    }), 201

@app.route('/tracks/<int:track_id>/comments', methods=['GET'])
def get_comments(track_id):
    track = Track.query.get_or_404(track_id)
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

@app.route('/users/<int:user_id>/stats', methods=['GET'])
@token_required
def get_user_stats(current_user, user_id):
    if current_user.id != user_id:
        return jsonify({'message': 'Unauthorized!'}), 403
    
    user = User.query.get_or_404(user_id)
    
    return jsonify({
        'votes_count': user.votes_count,
        'submissions_count': user.submissions_count,
        'trust_score': user.trust_score,
        'comments_count': Comment.query.filter_by(user_id=user_id).count(),
        'member_since': user.created_at.isoformat()
    })

@app.route('/tracks/trending', methods=['GET'])
def get_trending_tracks():
    limit = int(request.args.get('limit', 20))
    
    cache_key = f"trending_{limit}"
    cached_result = APICache.get_cached(cache_key)
    if cached_result:
        return jsonify(cached_result)
    
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

@app.route('/tracks/top', methods=['GET'])
def get_top_tracks():
    period = request.args.get('period', 'weekly')
    limit = int(request.args.get('limit', 20))
    
    cache_key = f"top_{period}_{limit}"
    cached_result = APICache.get_cached(cache_key)
    if cached_result:
        return jsonify(cached_result)
    
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

@app.route('/status', methods=['GET'])
def system_status():
    return jsonify({
        'status': 'online',
        'version': '1.0.0',
        'tracks_count': Track.query.count(),
        'users_count': User.query.count(),
        'votes_count': Vote.query.count(),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Resource not found!'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'message': 'Internal server error!'}), 500

@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    import os
    with app.app_context():
        db.create_all()
    
    # Railway provides PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
