import sys
import json
import os
import hashlib
import mysql.connector
import numpy as np
import librosa
from scipy.ndimage import maximum_filter
from collections import Counter
import warnings

# 1. DATABASE CONFIGURATION
db_config = {
    'user': 'root',
    'password': 'Suhit@2004',  # <--- UPDATE THIS
    'host': 'localhost',
    'database': 'polyphonic'
}

# --- SETTINGS (MUST MATCH INGEST WORKER) ---
SAMPLE_RATE = 22050
FFT_WINDOW_SIZE = 2048

def generate_fingerprints(file_path):
    """
    (Same logic as ingest. ideally we would put this in a shared module,
     but for now we copy-paste to keep it simple).
    """
    try:
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
    except Exception:
        return []

def identify_audio(file_path):
    conn = None
    try:
        # 1. GENERATE FINGERPRINTS FOR THE QUERY
        # This is the "Unknown Clip"
        query_fingerprints = generate_fingerprints(file_path)
        
        if not query_fingerprints:
            return {"status": "error", "message": "No silence or audio data found"}

        # 2. QUERY THE DATABASE
        # We need to find ALL songs that contain ANY of these hashes.
        
        # Extract just the hash strings
        query_hashes = [h for (h, t) in query_fingerprints]
        
        # If we have too many hashes, we might break the query limit. 
        # Let's take a random sample of 1000 if it's huge, or just run it.
        # For this demo, we'll run all.
        
        format_strings = ','.join(['%s'] * len(query_hashes))
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # SELECT AudioId, Offset FROM AudioFingerprints WHERE Hash IN (...)
        sql = f"""
            SELECT AudioId, FingerprintOffset, FingerprintHash 
            FROM AudioFingerprint 
            WHERE FingerprintHash IN ({format_strings})
        """
        
        cursor.execute(sql, tuple(query_hashes))
        matches = cursor.fetchall()
        
        # 3. THE ALIGNMENT LOGIC (The "Histogram")
        # We need to calculate: (Database_Timestamp - Sample_Timestamp)
        
        # Create a dictionary to map Hash -> Sample_Timestamp for quick lookup
        # (Because one hash might appear multiple times in the sample, we handle that simply here)
        query_hash_map = {h: t for (h, t) in query_fingerprints}
        
        # List to store "Votes"
        # A vote is: (AudioID, TimeDifference)
        votes = []
        
        for (db_audio_id, db_offset, db_hash) in matches:
            if db_hash in query_hash_map:
                sample_offset = query_hash_map[db_hash]
                
                # The Golden Formula
                diff = db_offset - sample_offset
                
                votes.append((db_audio_id, diff))
        
        # 4. COUNT THE VOTES
        # We look for the AudioID that has the MOST consistent time difference
        if not votes:
            return {"status": "no_match", "message": "No matching fingerprints found"}

        vote_counts = Counter(votes)
        top_match = vote_counts.most_common(1)[0] 
        # top_match looks like: ((AudioId, TimeDiff), Count)
        
        best_audio_id = top_match[0][0]
        best_score = top_match[1]
        
        # Threshold: If we only have 2 matches, it's probably noise.
        if best_score < 5:
             return {"status": "no_match", "message": "Signal too weak"}

        # 5. FETCH SONG METADATA
        cursor.execute("SELECT AudioName, AudioMetadata FROM Audio WHERE AudioId = %s", (best_audio_id,))
        song_info = cursor.fetchone()
        
        return {
            "status": "match_found",
            "id": best_audio_id,
            "filename": song_info[0],
            "score": best_score,
            "metadata": json.loads(song_info[1]) if song_info[1] else {}
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error"}))
        sys.exit(1)
        
    print(json.dumps(identify_audio(sys.argv[1])))