import sys
import json
import hashlib
import numpy as np
import librosa
from scipy.ndimage import maximum_filter
from collections import Counter
import mysql.connector
import warnings
import os

# --- CONFIGURATION ---
SAMPLE_RATE = 22050
FFT_WINDOW_SIZE = 2048

def generate_fingerprints(file_path):
    """
    Generates the list of (hash, time) tuples.
    """
    # NO TRY/EXCEPT HERE - We want to know if Librosa fails
    y, sr = librosa.load(file_path, sr=SAMPLE_RATE)
    D = np.abs(librosa.stft(y, n_fft=FFT_WINDOW_SIZE))
    
    neighborhood_size = (20, 20)
    local_max = maximum_filter(D, size=neighborhood_size) == D
    background_noise = np.mean(D) * 1.5
    peaks = local_max & (D > background_noise)
    
    y_freq, x_time = np.where(peaks)
    
    hashes = []
    for i in range(len(x_time)):
        for j in range(1, 15):
            if (i + j) < len(x_time):
                t1, f1 = x_time[i], y_freq[i]
                t2, f2 = x_time[i + j], y_freq[i + j]
                delta_t = t2 - t1
                if delta_t > 100: break

                h_str = f"{f1}|{f2}|{delta_t}"
                h_val = hashlib.sha1(h_str.encode('utf-8')).hexdigest()[:32]
                time_ms = int(librosa.frames_to_time(t1, sr=sr) * 1000)
                hashes.append((h_val, time_ms))
    return hashes

def find_best_match(cursor, fingerprints):
    """
    Takes a DB cursor and a list of fingerprints.
    Returns (ParentID, Score).
    """
    if not fingerprints:
        return None, 0
        
    # Optimization: Sample first 2000 hashes
    search_sample = [h for (h, t) in fingerprints][:2000]
    
    if not search_sample:
        return None, 0

    format_strings = ','.join(['%s'] * len(search_sample))
    
    # Check DB for matches - UPDATED TO MATCH YOUR SCHEMA (AudioFingerprint)
    sql = f"""
        SELECT AudioId, FingerprintOffset, FingerprintHash 
        FROM AudioFingerprint 
        WHERE FingerprintHash IN ({format_strings})
    """
    cursor.execute(sql, tuple(search_sample))
    matches = cursor.fetchall()
    
    # Calculate Alignment
    query_hash_map = {h: t for (h, t) in fingerprints}
    votes = []
    
    for (db_audio_id, db_offset, db_hash) in matches:
        if db_hash in query_hash_map:
            sample_offset = query_hash_map[db_hash]
            diff = db_offset - sample_offset
            votes.append((db_audio_id, diff))
            
    if not votes:
        return None, 0

    vote_counts = Counter(votes)
    top_match = vote_counts.most_common(1)[0]
    
    parent_id = top_match[0][0]
    score = top_match[1]
    
    if score > 10: # Threshold
        return parent_id, score
    
    return None, 0

# --- STANDALONE EXECUTION (For /identify route) ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    db_config = {
        'user': os.environ.get('DB_USER'),
        'password': os.environ.get('DB_PASSWORD'),
        'host': os.environ.get('DB_HOST'),
        'database': os.environ.get('DB_DATABASE')
    }
    
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error"}))
        sys.exit(1)
        
    warnings.filterwarnings("ignore")
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        fprints = generate_fingerprints(sys.argv[1])
        match_id, score = find_best_match(cursor, fprints)
        
        if match_id:
            cursor.execute("SELECT AudioName FROM Audio WHERE AudioId = %s", (match_id,))
            res = cursor.fetchone()
            name = res[0] if res else "Unknown"
            print(json.dumps({"status": "match_found", "filename": name, "score": score, "id": match_id}))
        else:
            print(json.dumps({"status": "no_match"}))
            
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()