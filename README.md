Branch : Learn


Table Audio
contains sudioid name metadata actual audio and hash

Table fingerprint 
contains fingerprintid 
audioid
fingerprint hash and fnuerprint offset

An audio file hits the /uploads endpoint 
# why /uploads folder on device?
# what multer does
# what if two people upload same name?
Node spawns a process which whill call the fingerprint worker.py
python outputs text, node cathes
if erroe node catches
then it deletes the temporary audio files which used disk space as buffer (?) 
sends resukt to frontemd

fingerprintworker.py
generates hash of the audio to check duplicates SHA256 HASH

genrates fingerprint of teh audio:
loads audio, creates spectogram, finds peaks, ignores bg noise gets coordinates of peaks, do fo rpeaks relative to next 15 peaks or something (why)
convert into milliseconds
generates hash for each peak fingerprint, many figerprints per audio


ingestion:
puts shit into table audio and table fingerprint


seacrhworker.py

hits /indentify enpoint

learn how it identifies

return if it identified or no


code:

curl.exe -F "audio_file=@C:/Users/suhit/Susu/21/Projects/polyphonic-db/test_audio/sample_A_copy.wav" http://localhost:3000/upload
 curl.exe -F "audio_file=@C:/Users/suhit/Susu/21/Projects/polyphonic-db/test_audio/sample_A_copy.wav" http://localhost:3000/identify
To Do:

make sure teh passworxs are in .env file
that composite indexing shit
on delete cascade for the fingerprint
api end points not wokring
some songs generate duplicate hashes due to their structure






