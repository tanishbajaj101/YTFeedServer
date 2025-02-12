from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from .config import Config
from .models import db
from .routes import routes_bp
from .auth import auth_bp, init_oauth
from .services import update_top_videos

# Initialize Flask-Migrate and APScheduler
migrate = Migrate()
scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    init_oauth(app)

    # Configure CORS to allow both the Chrome extension and YouTube
    CORS(app, 
         supports_credentials=True, 
         origins=[
            "chrome-extension://jmllmfhiphjnhjjibbhoaamcncenlmao",
            "https://www.youtube.com"
         ],
         methods=["GET", "POST", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"]
    )

    # Register blueprints
    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    with app.app_context():
        update_top_videos()
        
    @scheduler.task('interval', id='update_top_videos', hours=24)
    def scheduled_update():
        with app.app_context():
            update_top_videos()

    # Start the scheduler
    scheduler.init_app(app)
    scheduler.start()

    return app
