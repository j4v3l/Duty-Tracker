"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class PersonnelBase(BaseModel):
    """Base personnel schema."""
    rank: str
    name: str
    is_active: bool = True


class PersonnelCreate(PersonnelBase):
    """Schema for creating personnel."""
    pass


class PersonnelResponse(PersonnelBase):
    """Schema for personnel responses."""
    id: int
    full_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class PostTypeBase(BaseModel):
    """Base post type schema."""
    name: str
    description: Optional[str] = None
    equipment_required: Optional[str] = None
    meeting_time: Optional[str] = None
    meeting_location: Optional[str] = None
    personnel_required: int = 1
    difficulty_weight: int = 1


class PostTypeCreate(PostTypeBase):
    """Schema for creating post types."""
    pass


class PostTypeResponse(PostTypeBase):
    """Schema for post type responses."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PostBase(BaseModel):
    """Base post schema."""
    name: str
    post_type_id: int
    is_active: bool = True


class PostCreate(PostBase):
    """Schema for creating posts."""
    pass


class PostResponse(PostBase):
    """Schema for post responses."""
    id: int
    created_at: datetime
    post_type: PostTypeResponse
    
    class Config:
        from_attributes = True


class AssignmentBase(BaseModel):
    """Base assignment schema."""
    person_id: int
    post_id: int
    duty_date: datetime
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "assigned"
    notes: Optional[str] = None


class AssignmentCreate(AssignmentBase):
    """Schema for creating assignments."""
    pass


class AssignmentResponse(AssignmentBase):
    """Schema for assignment responses."""
    id: int
    created_at: datetime
    person: PersonnelResponse
    post: PostResponse
    
    class Config:
        from_attributes = True


class FairnessStats(BaseModel):
    """Schema for fairness statistics."""
    person_id: int
    person_name: str
    total_assignments: int
    total_difficulty_points: int
    last_assignment_date: Optional[datetime] = None
    consecutive_standby: int
    fairness_score: float  # Calculated score for fairness


class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""
    total_personnel: int
    active_assignments: int
    posts_covered: int
    fairness_variance: float
    recent_assignments: List[AssignmentResponse]
