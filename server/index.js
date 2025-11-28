const express = require('express');
const multer = require('multer');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 3000;

// 1. CONFIGURE STORAGE (Multer)
// We need to tell Multer WHERE to save files and WHAT to name them.
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        // 'cb' stands for callback. It's how we tell Multer "Go ahead".
        // null means "no error", second arg is the folder path.
        // We go up one level (..) to get out of /server, then into /uploads
        cb(null, path.join(__dirname, '../uploads'));
    },
    filename: (req, file, cb) => {
        // We append the current timestamp to the filename to avoid overwrites.
        // "kick.wav" becomes "kick-16982323232.wav"
        const uniqueSuffix = Date.now();
        cb(null, file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname));
    }
});

const upload = multer({ storage: storage });

// 2. THE UPLOAD ROUTE
// This is the endpoint your React frontend will hit.
app.post('/uploads', upload.single('audio_file'), (req, res) => {
    
    // Check if a file was actually uploaded
    if (!req.file) {
        return res.status(400).send('No file uploaded.');
    }

    console.log(`File saved at: ${req.file.path}`);

    // 3. THE BRIDGE (Spawn Python)
    // We run the python command, passing the file path as an argument.
    const pythonProcess = spawn('python', [
        path.join(__dirname, '../scripts/fingerprint_worker.py'), // Script to run
        req.file.path                                            // Argument 1: The File Path
    ]);

    let dataBuffer = '';
    let stderrBuffer = '';

    // 4. LISTEN FOR DATA (stdout)
    // As Python prints text, Node catches it here.
    pythonProcess.stdout.on('data', (data) => {
        dataBuffer += data.toString();
    });

    // 5. LISTEN FOR ERRORS (stderr)
    // If Python crashes or prints to stderr, we capture it here for debugging.
    pythonProcess.stderr.on('data', (data) => {
        const msg = data.toString();
        stderrBuffer += msg;
        console.error(`Python Error: ${msg}`);
    });

    // 6. LISTEN FOR COMPLETION (close)
    // When Python calls quit() or finishes, this runs.
    pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
        console.log(`Python stdout: ${dataBuffer}`);
        if (stderrBuffer) console.log(`Python stderr: ${stderrBuffer}`);
        
        // Clean up: Delete the temp file so your hard drive doesn't fill up
        fs.unlink(req.file.path, (err) => {
            if (err) console.error("Failed to delete temp file:", err);
        });

        // Send the result back to the frontend
        try {
            // We expect Python to print a JSON string like {"status": "success", "id": 5}
            const result = JSON.parse(dataBuffer);
            res.json(result);
        } catch (e) {
            console.error('Failed to parse JSON from Python stdout:', e);
            const debugMessage = `Error parsing Python output: stdout=${dataBuffer} stderr=${stderrBuffer}`;
            res.status(500).send(debugMessage);
        }
    });
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});