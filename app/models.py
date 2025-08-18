"""Database models for the duty tracker application."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Personnel(Base):
    """Personnel model for tracking military personnel."""
    
    __tablename__ = "personnel"
    
    id = Column(Integer, primary_key=True, index=True)
    rank = Column(String(10), nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assignments = relationship("Assignment", back_populates="person")
    
    @property
    def full_name(self) -> str:
        """Return full name with rank."""
        return f"{self.rank} {self.name}"


class PostType(Base):
    """Post types model (SOG, CQ, ECP, VCP, ROVER, etc.)."""
    
    __tablename__ = "post_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    equipment_required = Column(Text)  # JSON string of required equipment
    meeting_time = Column(String(20))  # e.g., "0700"
    meeting_location = Column(String(100))  # e.g., "TOC"
    personnel_required = Column(Integer, default=1)  # How many people needed
    difficulty_weight = Column(Integer, default=1)  # For fairness calculations
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    posts = relationship("Post", back_populates="post_type")


class Post(Base):
    """Individual posts (ECP1, ECP2, etc.)."""
    
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # e.g., "ECP1", "ECP2"
    post_type_id = Column(Integer, ForeignKey("post_types.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post_type = relationship("PostType", back_populates="posts")
    assignments = relationship("Assignment", back_populates="post")


class Assignment(Base):
    """Assignment model linking personnel to posts."""
    
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("personnel.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    duty_date = Column(DateTime, nullable=False)
    start_time = Column(String(10))  # e.g., "0700"
    end_time = Column(String(10))    # e.g., "1900"
    status = Column(String(20), default="assigned")  # assigned, completed, no-show
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    person = relationship("Personnel", back_populates="assignments")
    post = relationship("Post", back_populates="assignments")


class FairnessTracking(Base):
    """Track fairness metrics for personnel assignments."""
    
    __tablename__ = "fairness_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("personnel.id"))
    total_assignments = Column(Integer, default=0)
    total_difficulty_points = Column(Integer, default=0)
    last_assignment_date = Column(DateTime)
    consecutive_standby = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    person = relationship("Personnel")
