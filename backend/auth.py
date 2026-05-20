import functools
from flask import abort, g, redirect, request, session, url_for
from passlib.hash import bcrypt
from backend.database import SessionLocal
from backend.models import User
from sqlalchemy.exc import IntegrityError


def authenticate(username: str, password: str):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if user and bcrypt.verify(password, user.password_hash):
        return user
    return None


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


def create_admin_user(username: str, password: str):
    db = SessionLocal()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.close()
        return existing
    user = User(username=username, password_hash=bcrypt.hash(password), is_admin=True)
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        db.close()
        return user
    except IntegrityError:
        db.rollback()
        existing = db.query(User).filter(User.username == username).first()
        db.close()
        return existing
