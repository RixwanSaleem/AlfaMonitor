
import os
from flask_socketio import SocketIO

# Force the simpler threading async mode to be compatible with Gunicorn gthread.
# CORS: allow configuring via ALLOWED_ORIGINS env var (comma-separated).
# If not provided, default to allowing all origins for convenience in development
# (set ALLOWED_ORIGINS in production to a comma-separated list of allowed origins).
raw_allowed = os.environ.get("ALLOWED_ORIGINS", "")
if raw_allowed:
    allowed_origins = raw_allowed.split(',')
else:
    allowed_origins = "*"

socketio = SocketIO(cors_allowed_origins=allowed_origins, async_mode="threading")


def emit_update(event: str, payload: dict):
    socketio.emit(event, payload, broadcast=True)
