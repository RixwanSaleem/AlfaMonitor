
import os
from flask_socketio import SocketIO

# Force the simpler threading async mode to be compatible with Gunicorn gthread.
# Restrict CORS to allowed origins only
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5000,http://127.0.0.1:5000").split(",")
socketio = SocketIO(cors_allowed_origins=allowed_origins, async_mode="threading")


def emit_update(event: str, payload: dict):
    socketio.emit(event, payload, broadcast=True)
