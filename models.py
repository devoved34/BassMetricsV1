"""
Database models for Dubstep Discovery Agent - Flask Web Version
"""

from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()


class Track(db.Model):
    """Track model for storing dubstep/riddim tracks."""
    
    __tablename__ = "tracks"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    artist = db.Column(db.String(255), nullable=False, index=True)
    normalized_title = db.Column(db.String(255), index=True)  # For fuzzy matching
    normalized_artist = db.Column(db.String(255), index=True)
    
    # Platform-specific IDs
    soundcloud_id = db.Column(db.String(100), unique=True, index=True)
    youtube_id = db.Column(db.String(100), unique=True, index=True)
    spotify_id = db.Column(db.String(100), unique=True, index=True)
    apple_music_id = db.Column(db.String(100), unique=True, index=True)
    
    # Metadata
    duration_ms = db.Column(db.Integer)
    genre = db.Column(db.String(100))
    subgenre = db.Column(db.String(100))
    release_date = db.Column(db.DateTime)
    
    # Aggregated metrics
    score = db.Column(db.Float, default=0.0)
    total_score = db.Column(db.Integer, default=0)
    vote_count = db.Column(db.Integer, default=0)
    engagement_score = db.Column(db.Float, default=0.0)
    growth_score = db.Column(db.Float, default=0.0)
    platform_count = db.Column(db.Integer, default=0)
    
    # Additional fields for web
    description = db.Column(db.Text)
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    platform_data = db.relationship("PlatformData", back_populates="track")
    votes = db.relationship("Vote", back_populates="track")
    comments = db.relationship("Comment", back_populates="track")
    
    def __repr__(self):
        return f'<Track {self.title} by {self.artist}>'


class PlatformData(db.Model):
    """Platform-specific data for tracks."""
    
    __tablename__ = "platform_data"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    track_id = db.Column(db.Integer, db.ForeignKey("tracks.id"), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # soundcloud, youtube, spotify, etc.
    
    # Metrics
    play_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    share_count = db.Column(db.Integer, default=0)
    popularity_score = db.Column(db.Float, default=0.0)
    
    # Platform-specific data
    platform_url = db.Column(db.String(500))
    url = db.Column(db.String(500))
    external_id = db.Column(db.String(255))
    thumbnail_url = db.Column(db.String(500))
    platform_metadata = db.Column(db.Text)  # JSON string for additional platform-specific data
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    track = db.relationship("Track", back_populates="platform_data")
    
    def set_metadata(self, data):
        self.platform_metadata = json.dumps(data)
    
    def get_metadata(self):
        if self.platform_metadata:
            return json.loads(self.platform_metadata)
        return {}
    
    def __repr__(self):
        return f'<PlatformData {self.platform}:{self.external_id}>'


class User(db.Model):
    """User model for community voting."""
    
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile
    display_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    
    # Verification
    is_verified = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Trust metrics
    trust_score = db.Column(db.Float, default=0.5)
    votes_count = db.Column(db.Integer, default=0)
    submissions_count = db.Column(db.Integer, default=0)
    account_age_days = db.Column(db.Integer, default=0)
    
    # Social links
    soundcloud_username = db.Column(db.String(100))
    spotify_username = db.Column(db.String(100))
    discord_username = db.Column(db.String(100))
    
    # Anti-fraud
    last_ip = db.Column(db.String(45))
    suspicious_activity = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    votes = db.relationship("Vote", back_populates="user")
    comments = db.relationship("Comment", back_populates="user")
    submitted_tracks = db.relationship("Track", backref="submitter", lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Vote(db.Model):
    """Vote model for track ratings."""
    
    __tablename__ = "votes"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey("tracks.id"), nullable=False)
    
    # Simple vote (1-10)
    score = db.Column(db.Integer)  # 1-10 rating
    simple_score = db.Column(db.Integer)  # 1-10 rating
    
    # Advanced vote breakdown
    drop_quality = db.Column(db.Float)      # 25% weight
    production = db.Column(db.Float)        # 20% weight
    bass_low_end = db.Column(db.Float)      # 20% weight
    originality = db.Column(db.Float)       # 15% weight
    buildup = db.Column(db.Float)           # 12% weight
    flow = db.Column(db.Float)              # 8% weight
    
    # Computed scores
    advanced_score = db.Column(db.Float)    # Weighted average
    final_score = db.Column(db.Float)       # Final computed score
    
    # Metadata
    vote_type = db.Column(db.String(20))    # "simple" or "advanced"
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    categories = db.Column(db.Text)
    confidence_score = db.Column(db.Float, default=1.0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User", back_populates="votes")
    track = db.relationship("Track", back_populates="votes")
    
    __table_args__ = (db.UniqueConstraint('user_id', 'track_id', name='unique_user_track_vote'),)
    
    def set_categories(self, categories_dict):
        self.categories = json.dumps(categories_dict)
    
    def get_categories(self):
        if self.categories:
            return json.loads(self.categories)
        return {}
    
    def __repr__(self):
        return f'<Vote {self.user_id}:{self.track_id}:{self.score}>'


class Comment(db.Model):
    """Comment model for sentiment analysis."""
    
    __tablename__ = "comments"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    track_id = db.Column(db.Integer, db.ForeignKey("tracks.id"), nullable=False)
    
    # Comment content
    text = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Sentiment analysis
    sentiment_score = db.Column(db.Float)     # -1 to 1
    sentiment_label = db.Column(db.String(20))  # positive, negative, neutral
    confidence = db.Column(db.Float)          # 0 to 1
    
    # Extracted features
    keywords = db.Column(db.Text)             # JSON string of musical keywords
    emotional_tones = db.Column(db.Text)      # JSON string of emotional descriptors
    
    # Metadata
    is_public = db.Column(db.Boolean, default=False)
    is_processed = db.Column(db.Boolean, default=False)
    is_flagged = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User", back_populates="comments")
    track = db.relationship("Track", back_populates="comments")
    
    def __repr__(self):
        return f'<Comment {self.id}:{self.user_id}:{self.track_id}>'


class WeeklyChart(db.Model):
    """Weekly chart snapshots."""
    
    __tablename__ = "weekly_charts"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    week_start = db.Column(db.DateTime, nullable=False, index=True)
    week_end = db.Column(db.DateTime, nullable=False)
    
    # Chart data
    chart_data = db.Column(db.Text)  # JSON string of top 50 tracks with all metrics
    
    # Metadata
    total_tracks = db.Column(db.Integer)
    total_votes = db.Column(db.Integer)
    total_users = db.Column(db.Integer)
    track_count = db.Column(db.Integer, default=0)
    genre_breakdown = db.Column(db.Text)
    platform_breakdown = db.Column(db.Text)
    
    # File paths
    json_file_path = db.Column(db.String(255))
    markdown_file_path = db.Column(db.String(255))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_chart_data(self, data):
        self.chart_data = json.dumps(data)
    
    def get_chart_data(self):
        if self.chart_data:
            return json.loads(self.chart_data)
        return []
    
    def set_genre_breakdown(self, data):
        self.genre_breakdown = json.dumps(data)
    
    def get_genre_breakdown(self):
        if self.genre_breakdown:
            return json.loads(self.genre_breakdown)
        return {}
    
    def set_platform_breakdown(self, data):
        self.platform_breakdown = json.dumps(data)
    
    def get_platform_breakdown(self):
        if self.platform_breakdown:
            return json.loads(self.platform_breakdown)
        return {}
    
    def __repr__(self):
        return f'<WeeklyChart {self.week_start}:{self.week_end}>'


class UserSession(db.Model):
    """User session tokens for web auth."""
    
    __tablename__ = "user_sessions"
    
    token = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", backref="sessions")
    
    def __repr__(self):
        return f'<UserSession {self.user_id}:{self.token[:10]}...>'


class APICache(db.Model):
    """API response caching for web performance."""
    
    __tablename__ = "api_cache"
    
    key = db.Column(db.String(255), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def get_cached(key):
        cache_entry = APICache.query.filter_by(key=key).first()
        if cache_entry and cache_entry.expires_at > datetime.utcnow():
            return json.loads(cache_entry.value)
        elif cache_entry:
            db.session.delete(cache_entry)
            db.session.commit()
        return None
    
    @staticmethod
    def set_cached(key, value, ttl_seconds=300):
        cache_entry = APICache.query.filter_by(key=key).first()
        if cache_entry:
            cache_entry.value = json.dumps(value)
            cache_entry.expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        else:
            cache_entry = APICache(
                key=key,
                value=json.dumps(value),
                expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds)
            )
            db.session.add(cache_entry)
        db.session.commit()
    
    def __repr__(self):
        return f'<APICache {self.key}>'
