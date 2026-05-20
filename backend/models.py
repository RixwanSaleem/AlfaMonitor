from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(128), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    is_admin = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Server(Base):
    __tablename__ = "servers"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    host = Column(String(256), nullable=False, unique=True)
    username = Column(String(128), nullable=False)
    password = Column(String(256), nullable=False)
    port = Column(Integer, default=22)
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
    metrics = relationship("Metric", back_populates="server", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="server", cascade="all, delete-orphan")


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    cpu_percent = Column(Integer)
    ram_percent = Column(Integer)
    disk_percent = Column(Integer)
    temperature = Column(String(64))
    services = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    server = relationship("Server", back_populates="metrics")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    level = Column(String(32), default="warning")
    message = Column(Text, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    server = relationship("Server", back_populates="alerts")


class PlaybookExecution(Base):
    __tablename__ = "playbook_executions"
    id = Column(Integer, primary_key=True)
    server_ids = Column(Text)  # JSON array of server IDs
    status = Column(String(32), default="pending")  # pending, running, success, failed
    output = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    return_code = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class NotificationSetting(Base):
    __tablename__ = "notification_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(128), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
