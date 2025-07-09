from flask import Blueprint, request, jsonify, session
from .models import db, VideoData, CachedVideoData, UserData
import time, requests

routes_bp = Blueprint('routes', __name__)

@routes_bp.route('/')
def home():
    return "Flask is running"

@routes_bp.route('/api/store-data', methods=['POST'])
def store_data():
    try:
        # 1. Extract Google ID Token from HTTP-only cookie
        id_token = request.cookies.get("google_id_token")
        if not id_token:
            return jsonify({"message": "Unauthorized"}), 401
        
        # 2. Verify the ID Token with Google
        response = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
        if response.status_code != 200:
            return jsonify({"message": "Invalid or expired token"}), 401

        user_data = response.json()
        user_google_id = user_data.get("sub")  # 'sub' is the unique Google ID

        if not user_google_id:
            return jsonify({"message": "Unauthorized"}), 401

        # 3. Get video URL and tags from request data
        data = request.get_json()
        video_url = data.get("video_url")
        tags = data.get("tags")

        if not video_url or not tags:
            return jsonify({"message": "Missing video_url or tags"}), 400

        video_id = video_url.split("watch?v=")[1].split("&")[0]
        tags = ",".join(tags)  # Convert list to comma-separated string
        timestamp = time.time()  # Get current timestamp

        today_start = time.time() - (time.time() % 86400)
        today_end = today_start + 86400 

        request_count = UserData.query.filter(
            UserData.google_id == user_google_id,
            UserData.timestamp >= today_start,
            UserData.timestamp < today_end
        ).count()

        if request_count >= 3:
            return jsonify({"message": "Daily request limit reached (3 per day)"}), 429  # Too many requests

        # 5. Check if the video already exists in the VideoData table
        existing_video = VideoData.query.filter_by(video_id=video_id).first()
        if existing_video:
            existing_video.count += 1
            db.session.commit()
        else:
            new_video = VideoData(video_id=video_id, tags=tags, timestamp=timestamp, count=1)
            db.session.add(new_video)
            db.session.commit()

            # 6. Store user-specific request data only if not already submitted
            existing_user_data = UserData.query.filter_by(
                google_id=user_google_id,
                video_id=video_id
            ).first()

            if not existing_user_data:
                new_user_data = UserData(
                    google_id=user_google_id,
                    video_id=video_id,
                    tags=tags,
                    timestamp=timestamp
                )
                db.session.add(new_user_data)
                db.session.commit()


        return jsonify({"message": "Data stored successfully"}), 200

    except Exception as e:
        print("Error occurred:", str(e))  # Debugging
        return jsonify({"message": f"Error storing data: {str(e)}"}), 500



@routes_bp.route('/api/get-data-by-tag/<tag>', methods=['GET'])
def get_data_by_tag(tag):
    try:
        matching_data = VideoData.query.filter(VideoData.tags.like(f"%{tag}%")).all()
        if matching_data:
            return jsonify([
                {"video_id": entry.video_id, "tags": entry.tags.split(","), "count": entry.count}
                for entry in matching_data
            ]), 200
        return jsonify({"message": f"No data found for tag: {tag}"}), 404
    except Exception as e:
        return jsonify({"message": f"Error fetching data by tag: {e}"}), 500

@routes_bp.route('/api/get-cached-videos/<tag>', methods=['GET'])
def get_cached_videos(tag):
    try:
        cached_videos = CachedVideoData.query.filter_by(tag_category=tag).all()
        if cached_videos:
            return jsonify([
                {"video_id": video.video_id, "title": video.title, "thumbnail_url": video.thumbnail_url,
                 "view_count": video.view_count, "video_created_at": video.video_created_at,
                 "channel_name": video.channel_name, "channel_photo_url": video.channel_photo_url}
                for video in cached_videos
            ]), 200
        return jsonify({"message": f"No cached videos found for tag: {tag}"}), 404
    except Exception as e:
        return jsonify({"message": f"Error fetching cached videos: {e}"}), 500

@routes_bp.route('/api/user-contributions', methods=['GET'])
def user_contributions():
    try:
        # Extract and verify Google ID token
        id_token = request.cookies.get("google_id_token")
        if not id_token:
            return jsonify({"message": "Unauthorized"}), 401
        
        response = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
        if response.status_code != 200:
            return jsonify({"message": "Invalid or expired token"}), 401

        user_data = response.json()
        user_google_id = user_data.get("sub")

        if not user_google_id:
            return jsonify({"message": "Unauthorized"}), 401

        # Query all videos contributed by this user
        user_videos = UserData.query.filter_by(google_id=user_google_id).all()

        # Fetch video details (assuming thumbnail and title come from another source)
        video_list = []
        for vid in user_videos:
            video_list.append({
                "video_id": vid.video_id,
                "tags": vid.tags,
                "timestamp": vid.timestamp,
                "thumbnail_url": f"https://img.youtube.com/vi/{vid.video_id}/hqdefault.jpg",
                "title": f"Video {vid.video_id}"  # Replace with actual title if available
            })

        return jsonify({"contributed_videos": video_list}), 200

    except Exception as e:
        print("Error occurred:", str(e))
        return jsonify({"message": f"Error retrieving data: {str(e)}"}), 500

