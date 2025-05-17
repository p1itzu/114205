from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class User(Base):
    __tablename__ = "users"
    id             = Column(Integer, primary_key=True, index=True)
    email          = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password= Column(String(255), nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    oauth_id       = Column(String(255), nullable=True)
    name           = Column(String(255), nullable=True)
    role           = Column(String(20), nullable=True)
    is_active      = Column(Boolean, default=True)
