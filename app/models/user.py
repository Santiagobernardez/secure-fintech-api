from sqlalchemy import Column, Integer, String, Boolean
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Security: Limit string length to prevent oversized payloads
    email = Column(String(255), unique=True, index=True, nullable=False)
    # Security: We will store hashes, NEVER plain text passwords
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)