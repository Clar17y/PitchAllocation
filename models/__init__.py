from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from sqlalchemy.exc import OperationalError
from allocator.logger import setup_logger

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'  # Redirect to login page if not authenticated
login_manager.login_message_category = 'info'

logger = setup_logger(__name__)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except OperationalError as e:
            logger.error(f"Failed to create database tables: {e}")
            # You might want to implement a retry mechanism here or raise an excepti