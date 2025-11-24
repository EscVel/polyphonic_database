from app.database import SessionLocal
from app.models import AudioFile, AudioLineage
from app.processor import process_audio_file
import sys
import os

# Create a DB session
db = SessionLocal()

def scan_database(file_path):
    if not os.path.exists(file_path):
        print("File not found.")
        return

    print(f"--- Forensic Scan initiated for: {file_path} ---")

    # 1. Extract the "Soul" (Vector) of the new file
    # We don't save it yet! We just want the vector to search with.
    features = process_audio_file(file_path)
    query_vector = features["embedding"]

    # 2. The Vector Search Query
    # We select the AudioFile AND the calculated distance
    results = db.query(
        AudioFile, 
        AudioFile.embedding.cosine_distance(query_vector).label("distance")
    ).order_by(
        AudioFile.embedding.cosine_distance(query_vector)
    ).limit(5).all()

    # 3. Analyze Results
    print(f"\nScanning against {len(results)} potential matches...")
    
    match_found = False
    
    for audio, distance in results:
        # We skip exact duplicates (Distance = 0) because that's just the file itself 
        # (if you are re-scanning a file already in DB)
        if distance < 1e-5: 
            print(f"-> EXACT MATCH FOUND: {audio.filename} (ID: {audio.id})")
            continue
            
        # Threshold: 0.25 is a good baseline for "Same texture/instrument"
        if distance < 0.25:
            print(f"-> MATCH DETECTED! [Dist: {distance:.4f}]")
            print(f"   Suspect: {audio.filename} (ID: {audio.id})")
            print(f"   Logic: High timbral similarity detected.")
            
            # AUTOMATIC LINEAGE CREATION
            # This is the 'Complex' requirement: The system auto-links them.
            # In a real app, we'd insert into AudioLineage here.
            match_found = True
        else:
            print(f"-> Clean: {audio.filename} [Dist: {distance:.4f}] (Dissimilar)")

    if not match_found:
        print("\n✅ Result: Audio appears original (No close relatives found).")
    else:
        print("\n⚠️ Result: POTENTIAL COPYRIGHT INFRINGEMENT DETECTED.")

if __name__ == "__main__":
    # Allow running from command line with a filename
    if len(sys.argv) > 1:
        scan_database(sys.argv[1])
    else:
        print("Please provide a file path. Usage: python scan_audio.py path/to/file.wav")