from flask_sqlalchemy import SQLAlchemy
import time

db = SQLAlchemy()

# stores the data of the user -> google_id, email and first_name
class User(db.Model):
    __tablename__ = 'user'
    google_id = db.Column(db.String(100), primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)

    # Define a one-to-many relationship with UserData using primaryjoin
    user_data = db.relationship(
        'UserData',
        back_populates='user',
        lazy=True,
        cascade="all, delete-orphan",
        primaryjoin="User.google_id == UserData.google_id"
    )

    def __repr__(self):
        return f"<User {self.first_name} - {self.google_id}>"
    

class UserData(db.Model):
    __tablename__ = 'user_data'
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), db.ForeignKey('user.google_id', ondelete="CASCADE"), nullable=False)
    video_id = db.Column(db.String(500), db.ForeignKey('video_data.video_id', ondelete="CASCADE"), nullable=False)  
    tags = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.Float, default=time.time)  # Store Unix timestamp as float

    user = db.relationship('User', back_populates='user_data')
    video = db.relationship('VideoData', back_populates='user_data') 
    
    def __repr__(self):
        return f"<UserData {self.video_id} - {self.tags}>"

    
class VideoData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(500), nullable=False, unique=True)
    tags = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.Float, default=time.time)  # Store Unix timestamp as float
    count = db.Column(db.Integer, default=1)

    user_data = db.relationship('UserData', back_populates='video', lazy=True)

    def __repr__(self):
        return f"<VideoData {self.video_id} - {self.tags}>"

class CachedVideoData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(500), nullable=False)
    tag_category = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(500))
    thumbnail_url = db.Column(db.String(500))
    view_count = db.Column(db.Integer)
    video_created_at = db.Column(db.String(100))
    channel_name = db.Column(db.String(200))
    channel_photo_url = db.Column(db.String(500))
    cache_timestamp = db.Column(db.Float, default=time.time)  # Store Unix timestamp as float

    def __repr__(self):
        return f"<CachedVideoData {self.video_id} - {self.tag_category}>"
