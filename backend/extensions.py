from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
db = SQLAlchemy()
