from app.database import SessionLocal
from app.models import AudioLineage

db = SessionLocal()

# We assume you have ID 1 and ID 2 in your DB from the previous steps.
# We are manually telling the DB: "File 1 is the Parent of File 2"
# In the real app, the scanner we wrote in Phase 4 would do this automatically.

link = AudioLineage(
    parent_id=1,   # The Original
    child_id=2,    # The Remix
    similarity_score=0.15
)

db.add(link)
db.commit()
print("Link created! File 1 is now the parent of File 2.")
db.close()