from app.database import SessionLocal, engine
from app.models import AudioFile
from app.processor import process_audio_file
import os

# Create a DB session
db = SessionLocal()

def upload_track(file_path):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return

    print(f"--- Starting Ingestion for {file_path} ---")
    
    # 1. Run the Signal Processing (The CPU heavy part)
    data = process_audio_file(file_path)
    
    # 2. Check for Duplicates (The Hash check)
    existing = db.query(AudioFile).filter(AudioFile.file_hash == data["file_hash"]).first()
    if existing:
        print(f"Skipping: File already exists in DB (ID: {existing.id})")
        return

    # 3. Create the Database Object
    new_audio = AudioFile(
        filename=data["filename"],
        file_hash=data["file_hash"],
        duration_seconds=data["duration"],
        binary_data=data["binary_data"],
        embedding=data["embedding"] # This is the list of 128 floats
    )
    
    # 4. Save to DB
    db.add(new_audio)
    db.commit()
    db.refresh(new_audio)
    
    print(f"Success! Saved {data['filename']} with ID: {new_audio.id}")
    print(f"Vector stored (first 5 dims): {data['embedding'][:5]}...")

# Run the test
# Make sure you have these files in your test_audio folder!
upload_track("test_audio/sample_A.wav")
upload_track("test_audio/sample_B.wav")

db.close()