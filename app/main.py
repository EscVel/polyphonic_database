from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import AudioFile

app = FastAPI(title="Polyphonic Gene-Splicer")

@app.get("/")
def read_root():
    return {"message": "System Online"}

@app.get("/files/")
def list_files(db: Session = Depends(get_db)):
    """List all audio files in the system"""
    return db.query(AudioFile).all()

@app.get("/lineage/{audio_id}")
def get_lineage(audio_id: int, db: Session = Depends(get_db)):
    """
    THE COMPLEX DBMS PART:
    Performs a Recursive CTE to find the ancestry of a sound.
    """
    
    # This is raw SQL because SQLAlchemy's recursive syntax is very verbose.
    # This query walks up the tree from Child -> Parent -> Grandparent
    recursive_query = text("""
    WITH RECURSIVE lineage_tree AS (
        -- Base Case: Start with the requested file
        SELECT 
            af.id, 
            af.filename, 
            0 as level, 
            NULL::int as parent_id
        FROM audio_files af
        WHERE af.id = :start_id
        
        UNION ALL
        
        -- Recursive Step: Find parents of the current row
        SELECT 
            parent.id, 
            parent.filename, 
            lt.level + 1,
            al.parent_id
        FROM audio_files parent
        JOIN audio_lineage al ON parent.id = al.parent_id
        JOIN lineage_tree lt ON al.child_id = lt.id
    )
    SELECT * FROM lineage_tree;
    """)
    
    try:
        results = db.execute(recursive_query, {"start_id": audio_id}).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Format the data for the API
    tree_data = []
    for row in results:
        tree_data.append({
            "id": row.id,
            "filename": row.filename,
            "generation_level": row.level,
            "parent_id": row.parent_id
        })
        
    return {"root_id": audio_id, "ancestry": tree_data}