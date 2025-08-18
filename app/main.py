"""Main FastAPI application."""

import json
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db, create_tables
from app import crud, schemas, models
from app.models import Base

# Create FastAPI app
app = FastAPI(
    title="Duty Tracker",
    description="Military duty assignment tracking system",
    version="0.1.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    """Create database tables and initialize data."""
    create_tables()
    await initialize_data()


async def initialize_data():
    """Initialize database with default data."""
    db = next(get_db())
    
    # Check if data already exists
    if db.query(models.Personnel).first():
        db.close()
        return
    
    # Create post types
    post_types_data = [
        {
            "name": "SOG",
            "description": "Staff Officer of the Guard",
            "equipment_required": json.dumps(["OCP's", "IOTV", "ACH", "Pistol Holster"]),
            "meeting_time": "0700",
            "meeting_location": "TOC",
            "personnel_required": 1,
            "difficulty_weight": 5
        },
        {
            "name": "CQ",
            "description": "Charge of Quarters",
            "equipment_required": json.dumps(["OCP's"]),
            "meeting_time": "0700",
            "meeting_location": "TOC",
            "personnel_required": 1,
            "difficulty_weight": 3
        },
        {
            "name": "ECP",
            "description": "Entry Control Point",
            "equipment_required": json.dumps(["OCP's", "ACH", "Wet Weather Gear", "Pistol Holster", "IOTV", "Thermacell"]),
            "meeting_time": "0615",
            "meeting_location": "Front of C10",
            "personnel_required": 2,
            "difficulty_weight": 4
        },
        {
            "name": "VCP",
            "description": "Vehicle Control Point",
            "equipment_required": json.dumps(["OCP's", "Wet Weather Gear"]),
            "meeting_time": "0645",
            "meeting_location": "Front of C10",
            "personnel_required": 2,
            "difficulty_weight": 3
        },
        {
            "name": "ROVER",
            "description": "Rover Patrol",
            "equipment_required": json.dumps(["OCP's", "Wet Weather Gear"]),
            "meeting_time": "0645",
            "meeting_location": "Front of C10",
            "personnel_required": 2,
            "difficulty_weight": 3
        },
        {
            "name": "Stand by",
            "description": "Stand by personnel",
            "equipment_required": json.dumps([]),
            "meeting_time": None,
            "meeting_location": None,
            "personnel_required": 1,
            "difficulty_weight": 1
        }
    ]
    
    for pt_data in post_types_data:
        post_type = models.PostType(**pt_data)
        db.add(post_type)
    
    db.commit()
    
    # Create posts
    posts_data = [
        {"name": "SOG", "post_type_id": 1},
        {"name": "CQ", "post_type_id": 2},
        {"name": "ECP1", "post_type_id": 3},
        {"name": "ECP2", "post_type_id": 3},
        {"name": "ECP3", "post_type_id": 3},
        {"name": "VCP", "post_type_id": 4},
        {"name": "ROVER", "post_type_id": 5},
        {"name": "Stand by", "post_type_id": 6},
    ]
    
    for post_data in posts_data:
        post = models.Post(**post_data)
        db.add(post)
    
    db.commit()
    
    # Create personnel from the provided roster
    personnel_data = [
        {"rank": "SGT", "name": "Lastre"},
        {"rank": "SPC", "name": "Veneroso"},
        {"rank": "PFC", "name": "Palmer"},
        {"rank": "SPC", "name": "Ciceron"},
        {"rank": "PV2", "name": "Kent"},
        {"rank": "SPC", "name": "Velasco"},
        {"rank": "SPC", "name": "Miller"},
        {"rank": "SPC", "name": "Tovar"},
        {"rank": "SPC", "name": "Presendieu"},
        {"rank": "SGT", "name": "Cerruti"},
        {"rank": "SGT", "name": "Garcia"},
        {"rank": "SPC", "name": "Matias-Rios"},
        {"rank": "SPC", "name": "Arguelles"},
        {"rank": "SPC", "name": "Hall"},
        {"rank": "SPC", "name": "Cole"},
        {"rank": "SPC", "name": "Revere"},
        {"rank": "SPC", "name": "Villaman"},
        {"rank": "PFC", "name": "Lawson"},
    ]
    
    for p_data in personnel_data:
        person = models.Personnel(**p_data)
        db.add(person)
    
    db.commit()
    db.close()


# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard page."""
    stats = crud.get_dashboard_stats(db)
    fairness_stats_raw = crud.get_fairness_stats(db)
    post_distribution_stats = crud.get_post_distribution_stats(db)
    
    # Convert SQLAlchemy objects to dictionaries for JSON serialization
    fairness_stats = []
    for fs in fairness_stats_raw:
        fs_dict = schemas.FairnessStats.model_validate(fs).model_dump()
        # Convert datetime to ISO string for JSON serialization
        if fs_dict.get('last_assignment_date'):
            fs_dict['last_assignment_date'] = fs_dict['last_assignment_date'].isoformat()
        fairness_stats.append(fs_dict)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "fairness_stats": fairness_stats,
            "post_distribution_stats": post_distribution_stats
        }
    )


@app.get("/api/personnel", response_model=List[schemas.PersonnelResponse])
def get_personnel(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all personnel."""
    return crud.get_personnel(db, skip=skip, limit=limit)


@app.post("/api/personnel", response_model=schemas.PersonnelResponse)
def create_personnel(personnel: schemas.PersonnelCreate, db: Session = Depends(get_db)):
    """Create new personnel."""
    return crud.create_personnel(db, personnel)


@app.get("/api/personnel/{person_id}/details")
def get_personnel_details(person_id: int, db: Session = Depends(get_db)):
    """Get comprehensive personnel details including assignment history and fairness stats."""
    details = crud.get_personnel_details(db, person_id)
    if not details:
        raise HTTPException(status_code=404, detail="Personnel not found")
    return details


@app.get("/api/posts", response_model=List[schemas.PostResponse])
def get_posts(db: Session = Depends(get_db)):
    """Get all posts."""
    return crud.get_posts(db)


@app.get("/api/post-types", response_model=List[schemas.PostTypeResponse])
def get_post_types(db: Session = Depends(get_db)):
    """Get all post types."""
    return crud.get_post_types(db)


@app.get("/api/assignments", response_model=List[schemas.AssignmentResponse])
def get_assignments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all assignments."""
    return crud.get_assignments(db, skip=skip, limit=limit)


@app.post("/api/assignments", response_model=schemas.AssignmentResponse)
def create_assignment(assignment: schemas.AssignmentCreate, db: Session = Depends(get_db)):
    """Create new assignment."""
    return crud.create_assignment(db, assignment)


@app.get("/api/fairness")
def get_fairness_stats(db: Session = Depends(get_db)):
    """Get fairness statistics for all personnel."""
    fairness_stats_raw = crud.get_fairness_stats(db)
    
    # Convert to dictionaries and handle datetime serialization
    fairness_stats = []
    for fs in fairness_stats_raw:
        fs_dict = schemas.FairnessStats.model_validate(fs).model_dump()
        if fs_dict.get('last_assignment_date'):
            fs_dict['last_assignment_date'] = fs_dict['last_assignment_date'].isoformat()
        fairness_stats.append(fs_dict)
    
    return fairness_stats


@app.get("/api/post-distribution")
def get_post_distribution_stats(db: Session = Depends(get_db)):
    """Get detailed post distribution statistics."""
    return crud.get_post_distribution_stats(db)


@app.post("/api/import-chat")
def import_chat_assignments(request: dict, db: Session = Depends(get_db)):
    """Import assignments from group chat format."""
    chat_text = request.get("chat_text", "")
    duty_date = request.get("duty_date", "")
    
    if not chat_text or not duty_date:
        raise HTTPException(status_code=400, detail="chat_text and duty_date are required")
    
    try:
        assignments_created = crud.parse_and_create_chat_assignments(db, chat_text, duty_date)
        return {"message": f"Successfully created {assignments_created} assignments", "count": assignments_created}
    except Exception as e:
        print(f"Error parsing chat: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error parsing chat: {str(e)}")


@app.post("/api/setup-posts")
def setup_posts(db: Session = Depends(get_db)):
    """Create all necessary posts for chat import."""
    from app.models import PostType, Post
    
    # Ensure all post types exist
    post_type_data = [
        ("SOG", "Sergeant of the Guard"),
        ("CQ", "Charge of Quarters"),
        ("ECP", "Entry Control Point"),
        ("VCP", "Vehicle Control Point"),
        ("ROVER", "Mobile Security"),
        ("Stand by", "Stand by Duty")
    ]
    
    for type_name, description in post_type_data:
        post_type = db.query(PostType).filter(PostType.name == type_name).first()
        if not post_type:
            post_type = PostType(name=type_name, description=description)
            db.add(post_type)
            db.commit()
            db.refresh(post_type)
    
    # Ensure all posts exist
    post_data = [
        ("SOG", "SOG"),
        ("CQ", "CQ"),
        ("ECP", "ECP1"),
        ("ECP", "ECP2"),
        ("ECP", "ECP3"),
        ("VCP", "VCP"),
        ("ROVER", "ROVER"),
        ("Stand by", "Stand by")
    ]
    
    created_posts = 0
    for type_name, post_name in post_data:
        post_type = db.query(PostType).filter(PostType.name == type_name).first()
        if post_type:
            existing_post = db.query(Post).filter(
                Post.post_type_id == post_type.id,
                Post.name == post_name
            ).first()
            
            if not existing_post:
                post = Post(
                    name=post_name,
                    post_type_id=post_type.id,
                    description=f"{post_name} duty post"
                )
                db.add(post)
                created_posts += 1
    
    db.commit()
    
    return {
        "success": True,
        "posts_created": created_posts,
        "message": f"Successfully created {created_posts} missing posts"
    }


@app.post("/api/recalculate-fairness")
def recalculate_fairness(db: Session = Depends(get_db)):
    """Recalculate fairness tracking for all existing assignments."""
    from app.models import FairnessTracking, Assignment
    
    try:
        # Clear existing fairness data
        db.query(FairnessTracking).delete()
        
        # Get all assignments
        assignments = db.query(Assignment).all()
        
        updated_count = 0
        for assignment in assignments:
            crud.update_fairness_tracking(db, assignment.person_id, assignment.post_id)
            updated_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Recalculated fairness tracking for {updated_count} assignments"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error recalculating fairness: {str(e)}")


@app.get("/api/dashboard")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    return crud.get_dashboard_stats(db)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
