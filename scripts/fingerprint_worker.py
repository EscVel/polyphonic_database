import sys
import json
import os
import hashlib
import mysql.connector

# 1. DATABASE CONFIGURATION
# Replace these with your actual Workbench credentials
db_config = {
    'user': 'root',
    'password': 'Suhit@2004',  # <--- UPDATE THIS
    'host': 'localhost',
    'database': 'polyphonic'   # <--- Ensure this matches your Schema name
}

def get_file_hash(file_path):
    """Generates a SHA-256 hash of the file to detect duplicates."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read the file in chunks so we don't crash RAM with big files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def ingest_file(file_path):
    conn = None
    try:
        # 2. CONNECT TO MYSQL
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 3. CALCULATE HASH
        file_hash = get_file_hash(file_path)

        # 4. CHECK FOR DUPLICATES
        # We look up if this hash already exists in Table A
        query_check = "SELECT AudioId FROM Audio WHERE AudioHash = %s"
        cursor.execute(query_check, (file_hash,))
        existing_file = cursor.fetchone()

        if existing_file:
            # If it exists, return the old ID. Don't re-upload.
            return {"status": "exists", "id": existing_file[0], "message": "Duplicate file detected"}

        # 5. PREPARE DATA FOR INSERTION
        # Read the raw binary data
        with open(file_path, 'rb') as f:
            binary_data = f.read()
        
        filename = os.path.basename(file_path)
        
        # Placeholder metadata (We will expand this later with Librosa)
        metadata = json.dumps({"description": "Uploaded via Polyphonic API"})

        # 6. INSERT INTO TABLE A
        # Note: We use %s as placeholders to prevent SQL Injection
        query_insert = """
            INSERT INTO Audio (AudioName, AudioHash, AudioFile, AudioMetadata) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query_insert, (filename, file_hash, binary_data, metadata))
        conn.commit() # Save the changes

        new_id = cursor.lastrowid
        return {"status": "success", "id": new_id, "message": "File processed successfully"}

    except mysql.connector.Error as err:
        return {"status": "error", "message": str(err)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# 7. THE ENTRY POINT
if __name__ == "__main__":
    # sys.argv[0] is the script name
    # sys.argv[1] is the file path sent by Node.js
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "No file path provided"}))
        sys.exit(1)

    input_path = sys.argv[1]
    
    # Run the logic
    result = ingest_file(input_path)
    
    # Print JSON to stdout (This is what Node.js reads)
    print(json.dumps(result))