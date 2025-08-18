"""CRUD operations for database models."""

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models import Personnel, PostType, Post, Assignment, FairnessTracking
from app.schemas import (
    PersonnelCreate, PostTypeCreate, PostCreate, AssignmentCreate, FairnessStats
)


def get_personnel(db: Session, skip: int = 0, limit: int = 100) -> List[Personnel]:
    """Get all personnel."""
    return db.query(Personnel).filter(Personnel.is_active == True).offset(skip).limit(limit).all()


def get_personnel_by_id(db: Session, person_id: int) -> Optional[Personnel]:
    """Get personnel by ID."""
    return db.query(Personnel).filter(Personnel.id == person_id).first()


def create_personnel(db: Session, personnel: PersonnelCreate) -> Personnel:
    """Create new personnel."""
    db_personnel = Personnel(**personnel.dict())
    db.add(db_personnel)
    db.commit()
    db.refresh(db_personnel)
    return db_personnel


def get_post_types(db: Session) -> List[PostType]:
    """Get all post types."""
    return db.query(PostType).all()


def create_post_type(db: Session, post_type: PostTypeCreate) -> PostType:
    """Create new post type."""
    db_post_type = PostType(**post_type.dict())
    db.add(db_post_type)
    db.commit()
    db.refresh(db_post_type)
    return db_post_type


def get_posts(db: Session) -> List[Post]:
    """Get all posts."""
    return db.query(Post).filter(Post.is_active == True).all()


def create_post(db: Session, post: PostCreate) -> Post:
    """Create new post."""
    db_post = Post(**post.dict())
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def get_assignments(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    duty_date: Optional[datetime] = None
) -> List[Assignment]:
    """Get assignments with optional date filter."""
    query = db.query(Assignment)
    if duty_date:
        query = query.filter(Assignment.duty_date == duty_date)
    return query.order_by(desc(Assignment.duty_date)).offset(skip).limit(limit).all()


def create_assignment(db: Session, assignment: AssignmentCreate) -> Assignment:
    """Create new assignment and update fairness tracking."""
    db_assignment = Assignment(**assignment.dict())
    db.add(db_assignment)
    
    # Update fairness tracking
    update_fairness_tracking(db, assignment.person_id, assignment.post_id)
    
    db.commit()
    db.refresh(db_assignment)
    return db_assignment


def update_fairness_tracking(db: Session, person_id: int, post_id: int):
    """Update fairness tracking for a person."""
    # Get or create fairness tracking record
    fairness = db.query(FairnessTracking).filter(
        FairnessTracking.person_id == person_id
    ).first()
    
    if not fairness:
        fairness = FairnessTracking(
            person_id=person_id,
            total_assignments=0,
            total_difficulty_points=0,
            consecutive_standby=0
        )
        db.add(fairness)
    
    # Ensure None values are treated as 0
    if fairness.total_assignments is None:
        fairness.total_assignments = 0
    if fairness.total_difficulty_points is None:
        fairness.total_difficulty_points = 0
    if fairness.consecutive_standby is None:
        fairness.consecutive_standby = 0
    
    # Get post difficulty weight
    post = db.query(Post).filter(Post.id == post_id).first()
    if post and post.post_type:
        difficulty_weight = post.post_type.difficulty_weight or 1
    else:
        difficulty_weight = 1
    
    # Update tracking
    fairness.total_assignments += 1
    fairness.total_difficulty_points += difficulty_weight
    fairness.last_assignment_date = datetime.utcnow()
    
    # Reset standby count if assigned to a real post
    if post and post.post_type.name != "Stand by":
        fairness.consecutive_standby = 0
    elif post and post.post_type.name == "Stand by":
        fairness.consecutive_standby += 1


def get_fairness_stats(db: Session) -> List[FairnessStats]:
    """Get fairness statistics for all personnel."""
    results = db.query(
        Personnel,
        FairnessTracking
    ).outerjoin(
        FairnessTracking, Personnel.id == FairnessTracking.person_id
    ).filter(Personnel.is_active == True).all()
    
    stats = []
    for person, tracking in results:
        if tracking:
            # Calculate fairness score (lower is more fair/needs more assignments)
            fairness_score = tracking.total_difficulty_points
            
            # Adjust for time since last assignment
            if tracking.last_assignment_date:
                days_since = (datetime.utcnow() - tracking.last_assignment_date).days
                fairness_score -= days_since * 0.1  # Small bonus for waiting
            
            stats.append(FairnessStats(
                person_id=person.id,
                person_name=person.full_name,
                total_assignments=tracking.total_assignments,
                total_difficulty_points=tracking.total_difficulty_points,
                last_assignment_date=tracking.last_assignment_date,
                consecutive_standby=tracking.consecutive_standby,
                fairness_score=fairness_score
            ))
        else:
            # New person with no assignments
            stats.append(FairnessStats(
                person_id=person.id,
                person_name=person.full_name,
                total_assignments=0,
                total_difficulty_points=0,
                last_assignment_date=None,
                consecutive_standby=0,
                fairness_score=0.0  # Highest priority for new assignments
            ))
    
    # Sort by fairness score (ascending = most deserving first)
    return sorted(stats, key=lambda x: x.fairness_score)


def get_post_distribution_stats(db: Session):
    """Get detailed post distribution statistics for fairness analysis."""
    # Get all assignments with personnel and post details
    assignments = db.query(Assignment).join(Personnel).join(Post).join(PostType).filter(
        Personnel.is_active == True
    ).all()
    
    # Group by person and post type
    person_post_stats = {}
    post_type_totals = {}
    
    for assignment in assignments:
        person_key = f"{assignment.person.id}_{assignment.person.full_name}"
        post_type = assignment.post.post_type.name
        
        if person_key not in person_post_stats:
            person_post_stats[person_key] = {
                'person_id': assignment.person.id,
                'person_name': assignment.person.full_name,
                'rank': assignment.person.rank,
                'post_types': {}
            }
        
        if post_type not in person_post_stats[person_key]['post_types']:
            person_post_stats[person_key]['post_types'][post_type] = 0
        
        person_post_stats[person_key]['post_types'][post_type] += 1
        
        # Track post type totals
        if post_type not in post_type_totals:
            post_type_totals[post_type] = 0
        post_type_totals[post_type] += 1
    
    # Calculate fairness metrics per post type
    results = []
    for person_key, person_data in person_post_stats.items():
        person_stats = {
            'person_id': person_data['person_id'],
            'person_name': person_data['person_name'],
            'rank': person_data['rank'],
            'post_assignments': []
        }
        
        total_assignments = sum(person_data['post_types'].values())
        
        for post_type, count in person_data['post_types'].items():
            percentage = (count / post_type_totals[post_type]) * 100 if post_type_totals[post_type] > 0 else 0
            person_stats['post_assignments'].append({
                'post_type': post_type,
                'count': count,
                'percentage_of_total': round(percentage, 1),
                'percentage_of_person': round((count / total_assignments) * 100, 1) if total_assignments > 0 else 0
            })
        
        person_stats['total_assignments'] = total_assignments
        person_stats['post_assignments'].sort(key=lambda x: x['count'], reverse=True)
        results.append(person_stats)
    
    # Sort by total assignments descending
    results.sort(key=lambda x: x['total_assignments'], reverse=True)
    
    return {
        'personnel_stats': results,
        'post_type_totals': post_type_totals,
        'total_assignments': sum(post_type_totals.values()),
        'total_personnel': len(results)
    }


def get_dashboard_stats(db: Session):
    """Get dashboard statistics."""
    total_personnel = db.query(Personnel).filter(Personnel.is_active == True).count()
    active_assignments = db.query(Assignment).filter(
        Assignment.duty_date >= datetime.utcnow().date()
    ).count()
    posts_covered = db.query(Post).filter(Post.is_active == True).count()
    
    # Calculate fairness variance
    fairness_stats = get_fairness_stats(db)
    if fairness_stats:
        scores = [stat.fairness_score for stat in fairness_stats]
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
    else:
        variance = 0.0
    
    # Get recent assignments and convert to dictionaries
    recent_assignments_raw = get_assignments(db, limit=5)
    recent_assignments = []
    for assignment in recent_assignments_raw:
        assignment_dict = {
            "id": assignment.id,
            "person_id": assignment.person_id,
            "post_id": assignment.post_id,
            "duty_date": assignment.duty_date.isoformat() if assignment.duty_date else None,
            "start_time": assignment.start_time,
            "end_time": assignment.end_time,
            "status": assignment.status,
            "notes": assignment.notes,
            "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
            "person": {
                "id": assignment.person.id,
                "rank": assignment.person.rank,
                "name": assignment.person.name
            } if assignment.person else None,
            "post": {
                "id": assignment.post.id,
                "name": assignment.post.name,
                "post_type": {
                    "id": assignment.post.post_type.id,
                    "name": assignment.post.post_type.name
                } if assignment.post.post_type else None
            } if assignment.post else None
        }
        recent_assignments.append(assignment_dict)
    
    return {
        "total_personnel": total_personnel,
        "active_assignments": active_assignments,
        "posts_covered": posts_covered,
        "fairness_variance": variance,
        "recent_assignments": recent_assignments
    }


def parse_and_create_chat_assignments(db: Session, chat_text: str, duty_date: str) -> int:
    """Parse group chat text and create assignments."""
    import re
    from datetime import datetime
    
    # Debug prints
    print(f"Parsing chat for date: {duty_date}")
    print(f"Chat text length: {len(chat_text)}")
    
    # Convert duty_date string to datetime object
    try:
        duty_date_obj = datetime.fromisoformat(duty_date).date()
        print(f"Parsed date: {duty_date_obj}")
    except:
        duty_date_obj = datetime.now().date()
        print(f"Using current date: {duty_date_obj}")
    
    assignments_created = 0
    current_post_type = None
    
    # Get all personnel and post mappings
    all_personnel = get_personnel(db)
    personnel_map = {}
    for p in all_personnel:
        # Create multiple lookup keys for flexibility
        full_name = f"{p.rank} {p.name}".upper()
        personnel_map[full_name] = p
        personnel_map[p.name.upper()] = p
        # Also add just the last name
        last_name = p.name.split()[-1].upper()
        personnel_map[last_name] = p
    
    print(f"Personnel map keys: {list(personnel_map.keys())[:10]}...")  # Show first 10
    
    post_types = {pt.name.upper(): pt for pt in get_post_types(db)}
    print(f"Post types: {list(post_types.keys())}")
    
    # Define post mappings based on the chat format
    post_mappings = {
        "SOG": {"type": "SOG", "posts": ["SOG"]},
        "CQ": {"type": "CQ", "posts": ["CQ"]},
        "ECP1": {"type": "ECP", "posts": ["ECP1"]},
        "ECP2": {"type": "ECP", "posts": ["ECP2"]}, 
        "ECP3": {"type": "ECP", "posts": ["ECP3"]},
        "VCP": {"type": "VCP", "posts": ["VCP"]},
        "ROVER": {"type": "ROVER", "posts": ["ROVER"]},
        "STAND BY": {"type": "Stand by", "posts": ["Stand by"]}
    }
    
    lines = chat_text.strip().split('\n')
    print(f"Processing {len(lines)} lines")
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        print(f"Line {i}: '{line}'")
            
        # Check for post type headers
        if "SOG:" in line:
            current_post_type = "SOG"
            print(f"Found SOG post type")
        elif "CQ:" in line:
            current_post_type = "CQ"
            print(f"Found CQ post type")
        elif "ECP1:" in line:
            current_post_type = "ECP1"
            print(f"Found ECP1 post type")
        elif "ECP2:" in line:
            current_post_type = "ECP2"
            print(f"Found ECP2 post type")
        elif "ECP3:" in line:
            current_post_type = "ECP3"
            print(f"Found ECP3 post type")
        elif "VCP:" in line:
            current_post_type = "VCP"
            print(f"Found VCP post type")
        elif "ROVER:" in line:
            current_post_type = "ROVER"
            print(f"Found ROVER post type")
        elif "Stand by:" in line:
            current_post_type = "STAND BY"
            print(f"Found Stand by post type")
        elif current_post_type and not line.startswith(('🚐', '💻', '🚧', '🛺', 'Meet at', 'OCP')):
            # This line should contain personnel names
            print(f"Processing names in line for {current_post_type}: {line}")
            # Extract rank and name pairs - more flexible pattern
            name_matches = re.findall(r'(PV2|PFC|SPC|CPL|SGT|SSG|SFC|MSG|SGM)\s+([A-Za-z][A-Za-z-]*)', line)
            print(f"Name matches found: {name_matches}")
            
            for rank, last_name in name_matches:
                print(f"Processing: {rank} {last_name}")
                # Try multiple matching strategies
                person = None
                search_keys = [
                    f"{rank} {last_name}".upper(),
                    last_name.upper(),
                    f"{rank.upper()} {last_name.upper()}"
                ]
                
                for key in search_keys:
                    if key in personnel_map:
                        person = personnel_map[key]
                        print(f"Found person with key '{key}': {person.rank} {person.name}")
                        break
                    
                    # Fuzzy matching - check if last_name is contained in any full name
                    for full_name, p in personnel_map.items():
                        if last_name.upper() in full_name and rank.upper() in full_name:
                            person = p
                            print(f"Found person via fuzzy match: {person.rank} {person.name}")
                            break
                    if person:
                        break
                
                if not person:
                    print(f"No person found for {rank} {last_name}")
                    continue
                
                if current_post_type in post_mappings:
                    # Find or create the post
                    post_type_name = post_mappings[current_post_type]["type"]
                    post_type = post_types.get(post_type_name.upper())
                    print(f"Looking for post type: {post_type_name} -> {post_type}")
                    
                    if post_type:
                        # Get the specific post for this type
                        post_name = post_mappings[current_post_type]["posts"][0]
                        post = db.query(Post).filter(
                            Post.post_type_id == post_type.id,
                            Post.name == post_name
                        ).first()
                        print(f"Looking for post: {post_name} -> {post}")
                        
                        if post:
                            # Check if assignment already exists to avoid duplicates
                            existing = db.query(Assignment).filter(
                                Assignment.person_id == person.id,
                                Assignment.post_id == post.id,
                                Assignment.duty_date == duty_date_obj
                            ).first()
                            
                            if not existing:
                                # Create the assignment
                                assignment = Assignment(
                                    person_id=person.id,
                                    post_id=post.id,
                                    duty_date=duty_date_obj,
                                    start_time="06:00",  # Default times
                                    end_time="18:00",
                                    status="assigned",
                                    notes=f"Imported from group chat"
                                )
                                
                                db.add(assignment)
                                db.flush()  # Get the assignment ID
                                
                                # Update fairness tracking
                                update_fairness_tracking(db, person.id, post.id)
                                
                                assignments_created += 1
                                print(f"Created assignment: {person.rank} {person.name} -> {post.name}")
                            else:
                                print(f"Assignment already exists for {person.rank} {person.name} on {duty_date_obj}")
                        else:
                            print(f"Post not found: {post_name}")
                    else:
                        print(f"Post type not found: {post_type_name}")
                else:
                    print(f"Unknown post type: {current_post_type}")
    
    print(f"Total assignments created: {assignments_created}")
    db.commit()
    return assignments_created


def get_personnel_details(db: Session, person_id: int) -> Optional[dict]:
    """Get comprehensive personnel details including assignment history and fairness stats."""
    person = db.query(Personnel).filter(Personnel.id == person_id).first()
    if not person:
        return None
    
    # Get all assignments for this person
    assignments = (
        db.query(Assignment)
        .filter(Assignment.person_id == person_id)
        .join(Post)
        .join(PostType)
        .order_by(Assignment.duty_date.desc())
        .all()
    )
    
    # Get fairness tracking data
    fairness_tracking = (
        db.query(FairnessTracking)
        .filter(FairnessTracking.person_id == person_id)
        .all()
    )
    
    # Calculate assignment statistics
    total_assignments = len(assignments)
    post_type_counts = {}
    post_counts = {}
    total_difficulty_points = 0
    recent_assignments = []
    
    for assignment in assignments:
        post_type_name = assignment.post.post_type.name
        post_name = assignment.post.name
        difficulty_weight = assignment.post.post_type.difficulty_weight
        
        # Count by post type
        post_type_counts[post_type_name] = post_type_counts.get(post_type_name, 0) + 1
        
        # Count by specific post
        post_counts[post_name] = post_counts.get(post_name, 0) + 1
        
        # Sum difficulty points
        total_difficulty_points += difficulty_weight
        
        # Recent assignments (last 10)
        if len(recent_assignments) < 10:
            recent_assignments.append({
                "id": assignment.id,
                "duty_date": assignment.duty_date.isoformat(),
                "post_name": post_name,
                "post_type": post_type_name,
                "start_time": assignment.start_time,
                "end_time": assignment.end_time,
                "status": assignment.status,
                "difficulty_weight": difficulty_weight,
                "notes": assignment.notes
            })
    
    # Calculate fairness score
    fairness_score = 0.0
    consecutive_standby = 0
    last_assignment_date = None
    
    if assignments:
        last_assignment_date = assignments[0].duty_date.isoformat()
        
        # Calculate fairness score based on recency and difficulty
        avg_difficulty = total_difficulty_points / total_assignments if total_assignments > 0 else 0
        # Convert both dates to the same type for comparison
        days_since_last = (datetime.now().date() - assignments[0].duty_date.date()).days
        fairness_score = avg_difficulty * 0.7 + (days_since_last * 0.1)
        
        # Count consecutive standby (if applicable)
        for assignment in assignments:
            if assignment.status == "standby":
                consecutive_standby += 1
            else:
                break
    
    # Get fairness tracking details (simplified since FairnessTracking is per person, not per post)
    fairness_details = []
    for tracking in fairness_tracking:
        fairness_details.append({
            "total_assignments": tracking.total_assignments,
            "total_difficulty_points": tracking.total_difficulty_points,
            "last_assignment_date": tracking.last_assignment_date.isoformat() if tracking.last_assignment_date else None,
            "consecutive_standby": tracking.consecutive_standby
        })
    
    return {
        "person_id": person.id,
        "rank": person.rank,
        "name": person.name,
        "full_name": person.full_name,
        "is_active": person.is_active,
        "created_at": person.created_at.isoformat(),
        "total_assignments": total_assignments,
        "total_difficulty_points": total_difficulty_points,
        "fairness_score": fairness_score,
        "consecutive_standby": consecutive_standby,
        "last_assignment_date": last_assignment_date,
        "post_type_counts": post_type_counts,
        "post_counts": post_counts,
        "recent_assignments": recent_assignments,
        "fairness_tracking": fairness_details,
        "assignment_summary": {
            "most_frequent_post_type": max(post_type_counts.items(), key=lambda x: x[1])[0] if post_type_counts else None,
            "most_frequent_post": max(post_counts.items(), key=lambda x: x[1])[0] if post_counts else None,
            "average_difficulty": total_difficulty_points / total_assignments if total_assignments > 0 else 0
        }
    }
