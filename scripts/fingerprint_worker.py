import sys
import json
import os
import hashlib
import mysql.connector
import warnings
from dotenv import load_dotenv

# --- IMPORT THE LIBRARY ---
import search_worker 

load_dotenv()

db_config = {
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('DB_HOST'),
    'database': os.environ.get('DB_DATABASE')
}

def get_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def ingest_file(file_path, original_filename=None):
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 1. CHECK DUPLICATE
        file_hash = get_file_hash(file_path)
        cursor.execute("SELECT AudioId FROM Audio WHERE AudioHash = %s", (file_hash,))
        existing = cursor.fetchone()
        if existing:
            return {"status": "exists", "id": existing[0], "message": "Duplicate file"}

        # 2. CALL LIBRARY TO GET FINGERPRINTS
        fingerprints = search_worker.generate_fingerprints(file_path)

        # 3. CALL LIBRARY TO FIND MATCHES
        parent_id, match_score = search_worker.find_best_match(cursor, fingerprints)

        # 4. INSERT NEW AUDIO
        with open(file_path, 'rb') as f:
            binary_data = f.read()
        
        filename = original_filename if original_filename else os.path.basename(file_path)
        
        metadata = {
            "detected_parent": parent_id if parent_id else None,
            "match_score": match_score
        }
        
        cursor.execute("""
            INSERT INTO Audio (AudioName, AudioHash, AudioFile, AudioMetadata) 
            VALUES (%s, %s, %s, %s)
        """, (filename, file_hash, binary_data, json.dumps(metadata)))
        
        new_child_id = cursor.lastrowid
        
        # 5. AUTO-LINK PARENT
        if parent_id:
            cursor.execute("""
                INSERT INTO derivations 
                (parentid, childid, transformationtype, transformationparameters) 
                VALUES (%s, %s, %s, %s)
            """, (
                parent_id, 
                new_child_id, 
                'AUTO_DETECTED', 
                json.dumps({"confidence_score": match_score})
            ))

        # 6. SAVE FINGERPRINTS (WITH DUPLICATE HANDLING)
        if fingerprints:
            # FIX A: Python De-duplication
            # Convert list of tuples to a SET, then back to LIST.
            # This removes any rows where (Hash, Time) are identical.
            unique_fingerprints = list(set(fingerprints))
            
            # Prepare values: (AudioId, Hash, Offset)
            bulk_values = [(new_child_id, h, t) for (h, t) in unique_fingerprints]
            
            # FIX B: SQL Safe Insert
            # We use 'INSERT IGNORE'. If a collision happens, MySQL skips that specific row
            # but continues inserting the others. It prevents the script from crashing.
            cursor.executemany("""
                INSERT IGNORE INTO AudioFingerprint (AudioId, FingerprintHash, FingerprintOffset) 
                VALUES (%s, %s, %s)
            """, bulk_values)

        conn.commit()

        return {
            "status": "success", 
            "id": new_child_id, 
            "parent_found": parent_id,
            "fingerprints_created": len(fingerprints),
            "message": "File processed via modular scripts"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    warnings.filterwarnings("ignore")
    
    input_path = sys.argv[1]
    original_filename = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(json.dumps(ingest_file(input_path, original_filename)))