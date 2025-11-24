import librosa
import numpy as np
import hashlib

def get_file_hash(file_bytes):
    """
    Generates a SHA-256 hash of the file.
    This acts as a digital fingerprint for EXACT duplicates.
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_bytes)
    return sha256_hash.hexdigest()

def extract_features(file_path):
    """
    The Magic Function.
    1. Loads audio.
    2. extracts MFCCs (The 'Vector').
    3. Returns all data needed for the DB.
    """
    print(f"Processing {file_path}...")
    
    # 1. Load the audio file using Librosa
    # y = audio time series, sr = sample rate
    y, sr = librosa.load(file_path, sr=None)
    
    # 2. Extract Duration
    duration = librosa.get_duration(y=y, sr=sr)
    
    # 3. Generate the Vector (MFCC)
    # We ask for 128 coefficients to match our DB column size.
    # This returns a matrix of shape (128, Time).
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=128)
    
    # 4. Collapse Time
    # The DB needs a single array of 128 numbers, not a matrix.
    # We take the AVERAGE of each coefficient across the whole file.
    # This represents the "Average Timbre" of the sound.
    mfcc_vector = np.mean(mfcc, axis=1)
    
    # Normalize vector (optional but good for cosine similarity)
    # It ensures the magnitude doesn't affect the comparison.
    norm = np.linalg.norm(mfcc_vector)
    if norm > 0:
        mfcc_vector = mfcc_vector / norm
        
    # Convert numpy array to a standard Python list for the DB
    vector_list = mfcc_vector.tolist()
    
    return vector_list, duration

def process_audio_file(file_path):
    """
    Orchestrates the whole process.
    """
    # Read raw bytes for storage
    with open(file_path, "rb") as f:
        raw_bytes = f.read()
        
    # Get the Hash
    file_hash = get_file_hash(raw_bytes)
    
    # Get the Vector and Metadata
    vector, duration = extract_features(file_path)
    
    return {
        "filename": file_path.split("/")[-1], # Gets just 'drum.wav'
        "binary_data": raw_bytes,
        "file_hash": file_hash,
        "duration": duration,
        "embedding": vector
    }