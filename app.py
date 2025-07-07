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
from functools import wraps

from config import Config
from models import db, User, Track, Vote, Comment, WeeklyChart, PlatformData, UserSession, APICache

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
CORS(app)
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

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

# Auth endpoints
@app.route('/auth/register', methods=['POST'])
@limiter.limit("10 per hour")
def register():
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

@app.route('/auth/login', methods=['POST'])
@limiter.limit("20 per hour")
def login():
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

    session_token = UserSession(token=token, user_id=user.id, expires_at=datetime.utcnow() + timedelta(hours=24))
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

# Charts and track endpoints
@app.route('/charts', methods=['GET'])
def get_charts():
    period = request.args.get('period', 'weekly')
    genre = request.args.get('genre', 'all')
    limit = int(request.args.get('limit', 20))

    cache_key = f"charts_{period}_{genre}_{limit}"
    cached = APICache.get_cached(cache_key)
    if cached:
        return jsonify(cached)

    query = Track.query
    if genre != 'all':
        query = query.filter(Track.genre == genre)

    now = datetime.utcnow()
    if period == 'weekly':
        query = query.filter(Track.created_at >= now - timedelta(days=7))
    elif period == 'monthly':
        query = query.filter(Track.created_at >= now - timedelta(days=30))

    tracks = query.order_by(Track.score.desc()).limit(limit).all()
    result = [track.to_dict() for track in tracks]
    APICache.set_cached(cache_key, result, 300)
    return jsonify(result)

@app.route('/tracks/search', methods=['GET'])
def search_tracks():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    limit = int(request.args.get('limit', 20))
    tracks = Track.query.filter(
        (Track.title.ilike(f'%{query}%')) | (Track.artist.ilike(f'%{query}%'))
    ).order_by(Track.score.desc()).limit(limit).all()
    return jsonify([track.to_dict() for track in tracks])

@app.route('/tracks', methods=['POST'])
@token_required
@limiter.limit("5 per hour")
def submit_track(current_user):
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

@app.route('/tracks/<int:track_id>/vote', methods=['POST'])
@token_required
@limiter.limit("50 per hour")
def vote_track(current_user, track_id):
    data = request.get_json()
    score = data.get('score')
    if not isinstance(score, int) or not (1 <= score <= 10):
        return jsonify({'message': 'Invalid score!'}), 400

    track = Track.query.get_or_404(track_id)
    if Vote.query.filter_by(user_id=current_user.id, track_id=track_id).first():
        return jsonify({'message': 'Already voted!'}), 400

    vote = Vote(user_id=current_user.id, track_id=track_id, score=score)
    db.session.add(vote)
    track.vote_count += 1
    track.total_score += score
    track.score = track.total_score / track.vote_count
    current_user.votes_count += 1
    current_user.trust_score += 1
    db.session.commit()

    return jsonify({'message': 'Vote submitted!', 'new_score': track.score})

@app.route('/tracks/<int:track_id>/comments', methods=['POST'])
@token_required
@limiter.limit("20 per hour")
def add_comment(current_user, track_id):
    text = request.get_json().get('text', '').strip()
    if len(text) < 5:
        return jsonify({'message': 'Comment too short!'}), 400

    comment = Comment(user_id=current_user.id, track_id=track_id, text=text)
    db.session.add(comment)
    current_user.trust_score += 1
    db.session.commit()
    return jsonify({'message': 'Comment added!', 'comment_id': comment.id}), 201

@app.route('/tracks/<int:track_id>/comments', methods=['GET'])
def get_comments(track_id):
    comments = Comment.query.filter_by(track_id=track_id).order_by(Comment.created_at.desc()).all()
    return jsonify([{
        'id': c.id,
        'text': c.text,
        'username': c.user.username,
        'created_at': c.created_at.isoformat(),
        'sentiment_score': c.sentiment_score
    } for c in comments])

@app.route('/users/<int:user_id>/stats', methods=['GET'])
@token_required
def get_user_stats(current_user, user_id):
    if current_user.id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    return jsonify({
        'votes_count': current_user.votes_count,
        'submissions_count': current_user.submissions_count,
        'trust_score': current_user.trust_score,
        'comments_count': Comment.query.filter_by(user_id=user_id).count(),
        'member_since': current_user.created_at.isoformat()
    })

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'online',
        'version': '1.0.0',
        'tracks_count': Track.query.count(),
        'users_count': User.query.count(),
        'votes_count': Vote.query.count(),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({'message': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return jsonify({'message': 'Internal server error'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
