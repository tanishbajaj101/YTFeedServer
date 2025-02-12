import time
from googleapiclient.discovery import build
from flask import current_app
from .models import db, VideoData, CachedVideoData
import logging

logger = logging.getLogger(__name__)

def fetch_youtube_data(video_id):
    try:
        youtube = build('youtube', 'v3', developerKey=current_app.config['YOUTUBE_API_KEY'])

        video_response = youtube.videos().list(
            part='snippet,statistics',
            id=video_id
        ).execute()

        if not video_response['items']:
            return None

        video_data = video_response['items'][0]
        channel_id = video_data['snippet']['channelId']

        channel_response = youtube.channels().list(
            part='snippet',
            id=channel_id
        ).execute()

        if not channel_response['items']:
            return None

        channel_data = channel_response['items'][0]

        return {
            'video_id': video_data['id'],
            'title': video_data['snippet']['title'],
            'thumbnail_url': video_data['snippet']['thumbnails']['high']['url'],
            'view_count': int(video_data['statistics']['viewCount']),
            'video_created_at': video_data['snippet']['publishedAt'],
            'channel_name': channel_data['snippet']['title'],
            'channel_photo_url': channel_data['snippet']['thumbnails']['high']['url']
        }
    except Exception as e:
        logger.error(f"Error fetching YouTube data: {e}")
        return None

def update_top_videos():
    try:
        with current_app.app_context():
            CachedVideoData.query.delete()
            db.session.commit()

            all_videos = VideoData.query.all()
            tag_categories = set(tag for video in all_videos for tag in video.tags.split(','))

            for tag in tag_categories:
                top_videos = VideoData.query.filter(VideoData.tags.like(f"%{tag}%"))\
                    .order_by(VideoData.count.desc()).limit(4).all()

                for video in top_videos:
                    youtube_data = fetch_youtube_data(video.video_id)
                    if youtube_data:
                        cached_video = CachedVideoData(
                            video_id=video.video_id,
                            tag_category=tag,
                            title=youtube_data['title'],
                            thumbnail_url=youtube_data['thumbnail_url'],
                            view_count=youtube_data['view_count'],
                            video_created_at=youtube_data['video_created_at'],
                            channel_name=youtube_data['channel_name'],
                            channel_photo_url=youtube_data['channel_photo_url'],
                            cache_timestamp=time.time()
                        )
                        db.session.add(cached_video)
                        video.count = 0

                db.session.commit()
    except Exception as e:
        logger.error(f"Error updating top videos: {e}")
        db.session.rollback()
