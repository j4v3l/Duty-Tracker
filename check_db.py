from app.database import SessionLocal
from app.models import Personnel, PostType, Post
from app.crud import get_personnel, get_post_types

db = SessionLocal()

print('=== PERSONNEL ===')
personnel = get_personnel(db)
for p in personnel:
    print(f'{p.id}: {p.rank} {p.name}')

print('\n=== POST TYPES ===')
post_types = get_post_types(db)
for pt in post_types:
    print(f'{pt.id}: {pt.name} - {pt.description}')

print('\n=== POSTS ===')
posts = db.query(Post).all()
for p in posts:
    print(f'{p.id}: {p.name} (Type: {p.post_type.name})')

db.close()
