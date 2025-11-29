import sys
import json
import os
import hashlib
import mysql.connector
import numpy as np
import librosa
from scipy.ndimage import maximum_filter
import warnings

import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Access the variables using os.environ.get()
# os.environ.get() reads environment variables
db_config = {
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'host': os.environ.get('DB_HOST'),
    'database': os.environ.get('DB_DATABASE')
}


# --- AUDIO SETTINGS ---
SAMPLE_RATE = 22050
FFT_WINDOW_SIZE = 2048
PEAK_AMPLITUDE_MIN = 10

def get_file_hash(file_path):
    """Generates a SHA-256 hash of the file to detect duplicates."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def generate_fingerprints(file_path):
    """
    Analyzes audio and returns a list of (hash, time_offset) tuples.
    """
    try:
        # 1. Load Audio (This can be slow, so we do it once)
        y, sr = librosa.load(file_path, sr=SAMPLE_RATE)

        # 2. Create Spectrogram (STFT)
        D = np.abs(librosa.stft(y, n_fft=FFT_WINDOW_SIZE))

        # 3. Find Peaks
        # neighborhood_size = (Frequency bin range, Time frame range)
        neighborhood_size = (20, 20)
        local_max = maximum_filter(D, size=neighborhood_size) == D
        
        # Noise gate: ignore quiet background noise
        background_noise = np.mean(D) * 1.5
        peaks = local_max & (D > background_noise)
        
        # Get coordinates of peaks
        y_freq, x_time = np.where(peaks)

        # 4. Create Hashes
        hashes = []
        for i in range(len(x_time)):
            for j in range(1, 15): # Look ahead at next 15 peaks
                if (i + j) < len(x_time):
                    t1, f1 = x_time[i], y_freq[i]
                    t2, f2 = x_time[i + j], y_freq[i + j]
                    
                    delta_t = t2 - t1
                    
                    if delta_t > 100: break # Too far away, stop looking

                    # Hash string: Freq1 | Freq2 | DeltaTime
                    h_str = f"{f1}|{f2}|{delta_t}"
                    h_val = hashlib.sha1(h_str.encode('utf-8')).hexdigest()[:32]
                    
                    # Convert Frame Index to Milliseconds
                    time_ms = int(librosa.frames_to_time(t1, sr=sr) * 1000)
                    
                    hashes.append((h_val, time_ms))
        # Print all generated hashes to the terminal for debugging/visibility
        try:
            #print(f"Generated {len(hashes)} fingerprints for: {file_path}")
            #for hh, tt in hashes:
            #    print(f"{hh} @ {tt}ms")
            pass
        except Exception:
            # Avoid breaking fingerprint generation if printing fails
            pass
        return hashes
    except Exception as e:
        # If audio processing fails (e.g. corrupt file), return empty list
        # In production, you might want to log this error specifically
        return []

def ingest_file(file_path, original_filename=None):
    conn = None
    try:
        # 2. CONNECT TO MYSQL
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 3. CALCULATE HASH
        file_hash = get_file_hash(file_path)

        # 4. CHECK FOR DUPLICATES (Table: Audio)
        query_check = "SELECT AudioId FROM Audio WHERE AudioHash = %s"
        cursor.execute(query_check, (file_hash,))
        existing_file = cursor.fetchone()

        if existing_file:
            return {"status": "exists", "id": existing_file[0], "message": "Duplicate file detected"}

        # 5. PREPARE DATA FOR INSERTION (Table: Audio)
        with open(file_path, 'rb') as f:
            binary_data = f.read()
        
        # Use original filename if provided, otherwise extract from temp file path
        filename = original_filename if original_filename else os.path.basename(file_path)
        
        # We store tech metadata about the analysis
        metadata = json.dumps({
            "engine": "librosa", 
            "sample_rate": SAMPLE_RATE,
            "original_upload_name": filename
        })

        # 6. INSERT INTO TABLE A (Audio)
        query_insert = """
            INSERT INTO Audio (AudioName, AudioHash, AudioFile, AudioMetadata) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query_insert, (filename, file_hash, binary_data, metadata))
        
        # Get the new ID to link the fingerprints
        new_id = cursor.lastrowid
        
        # 7. GENERATE & INSERT FINGERPRINTS (Table: AudioFingerprints)
        # Calculate the "DNA"
        fingerprint_list = generate_fingerprints(file_path)
        
        # Print the fingerprints that will be inserted (hash and offset)
        try:
            #print(f"Preparing to insert {len(fingerprint_list)} fingerprints for AudioId {new_id}")
            #for hh, tt in fingerprint_list:
            #    print(f"Insert -> {hh} @ {tt}ms")
            pass
        except Exception:
            pass

        if fingerprint_list:
            # Prepare for bulk insert: (AudioId, Hash, Offset)
            bulk_values = [(new_id, h, t) for (h, t) in fingerprint_list]
            
            # --- IMPORTANT: VERIFY YOUR TABLE 2 NAME HERE ---
            # I am assuming your second table is 'AudioFingerprints'
            # and columns are 'AudioId', 'FingerprintHash', 'TimeOffset'
            query_fingerprints = """
                INSERT INTO AudioFingerprint (AudioId, FingerprintHash, FingerprintOffset) 
                VALUES (%s, %s, %s)
            """
            # cursor.executemany(query_fingerprints, bulk_values)
            # try:
            #     print(f"Inserted {len(bulk_values)} fingerprints for AudioId {new_id}")
            # except Exception:
            #     pass

        conn.commit() # Save everything

        return {
            "status": "success", 
            "id": new_id, 
            "fingerprints_created": len(fingerprint_list),
            "message": "File processed successfully"
        }

    except mysql.connector.Error as err:
        return {"status": "error", "message": str(err)}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# 8. THE ENTRY POINT
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "No file path provided"}))
        sys.exit(1)

    # Clean up output: Librosa sometimes prints warnings that mess up JSON parsing
    warnings.filterwarnings("ignore")

    input_path = sys.argv[1]
    # If original filename was passed, store it for use in ingest_file
    original_filename = sys.argv[2] if len(sys.argv) > 2 else None
    result = ingest_file(input_path, original_filename)
    print(json.dumps(result))