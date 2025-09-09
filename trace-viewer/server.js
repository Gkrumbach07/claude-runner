const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

const app = express();
const port = process.env.PORT || 3000;
const artifactsDir = process.env.ARTIFACTS_DIR || '/artifacts';

// CORS configuration for security
const corsOptions = {
  origin: process.env.ALLOWED_ORIGINS ? process.env.ALLOWED_ORIGINS.split(',') : true,
  credentials: true,
  optionsSuccessStatus: 200
};

app.use(cors(corsOptions));
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'playwright-trace-viewer' });
});

// List available traces
app.get('/api/traces', (req, res) => {
  try {
    if (!fs.existsSync(artifactsDir)) {
      return res.json({ traces: [] });
    }

    const sessions = fs.readdirSync(artifactsDir, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory())
      .map(dirent => dirent.name);

    const traces = [];
    sessions.forEach(sessionName => {
      const sessionDir = path.join(artifactsDir, sessionName);
      if (fs.existsSync(sessionDir)) {
        const files = fs.readdirSync(sessionDir);
        files.forEach(file => {
          if (file.endsWith('.zip') && file.includes('trace')) {
            const filePath = path.join(sessionDir, file);
            const stats = fs.statSync(filePath);
            traces.push({
              sessionName,
              filename: file,
              path: filePath,
              size: stats.size,
              createdAt: stats.birthtime.toISOString(),
              viewerUrl: `/trace/${sessionName}/${file}`
            });
          }
        });
      }
    });

    res.json({ traces });
  } catch (error) {
    console.error('Error listing traces:', error);
    res.status(500).json({ error: 'Failed to list traces' });
  }
});

// Serve trace viewer for specific trace file
app.get('/trace/:sessionName/:traceFile', (req, res) => {
  const { sessionName, traceFile } = req.params;
  const tracePath = path.join(artifactsDir, sessionName, traceFile);

  if (!fs.existsSync(tracePath)) {
    return res.status(404).json({ error: 'Trace file not found' });
  }

  // Start Playwright trace viewer for this specific file
  // The trace viewer will be served on a different port and we'll proxy/redirect
  const viewerPort = 9323; // Default Playwright trace viewer port
  
  // Use Playwright's built-in trace viewer
  const traceViewer = spawn('npx', ['playwright', 'show-trace', tracePath, '--port', viewerPort.toString()], {
    stdio: 'pipe',
    detached: true
  });

  // Return HTML that embeds the trace viewer
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trace Viewer - ${sessionName}</title>
    <style>
        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
        }
        .trace-container {
            width: 100%;
            height: 100vh;
            border: none;
        }
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8f9fa;
        }
        .spinner {
            border: 4px solid #f3f3f4;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin-right: 16px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div>Loading trace viewer...</div>
    </div>
    <iframe 
        id="trace-viewer" 
        class="trace-container" 
        src="http://localhost:${viewerPort}"
        style="display: none;"
        onload="document.getElementById('loading').style.display='none'; this.style.display='block';"
    ></iframe>
    
    <script>
        // Fallback to show iframe after 3 seconds even if onload doesn't fire
        setTimeout(() => {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('trace-viewer').style.display = 'block';
        }, 3000);
    </script>
</body>
</html>`;

  res.setHeader('Content-Type', 'text/html');
  res.send(html);
});

// Serve artifacts (screenshots, PDFs, etc.)
app.get('/artifact/:sessionName/:filename', (req, res) => {
  const { sessionName, filename } = req.params;
  const artifactPath = path.join(artifactsDir, sessionName, filename);

  if (!fs.existsSync(artifactPath)) {
    return res.status(404).json({ error: 'Artifact not found' });
  }

  // Set appropriate content type based on file extension
  const ext = path.extname(filename).toLowerCase();
  const contentTypes = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.pdf': 'application/pdf',
    '.zip': 'application/zip'
  };

  const contentType = contentTypes[ext] || 'application/octet-stream';
  res.setHeader('Content-Type', contentType);
  
  // For images and PDFs, allow inline display
  if (['.png', '.jpg', '.jpeg', '.pdf'].includes(ext)) {
    res.setHeader('Content-Disposition', 'inline');
  }

  // Stream the file
  const stream = fs.createReadStream(artifactPath);
  stream.pipe(res);
});

// Get session artifacts
app.get('/api/session/:sessionName/artifacts', (req, res) => {
  const { sessionName } = req.params;
  const sessionDir = path.join(artifactsDir, sessionName);

  try {
    if (!fs.existsSync(sessionDir)) {
      return res.json({ artifacts: [] });
    }

    const files = fs.readdirSync(sessionDir);
    const artifacts = files.map(filename => {
      const filePath = path.join(sessionDir, filename);
      const stats = fs.statSync(filePath);
      
      let type = 'unknown';
      if (filename.includes('trace') && filename.endsWith('.zip')) {
        type = 'trace';
      } else if (filename.match(/\.(png|jpg|jpeg)$/i)) {
        type = 'screenshot';
      } else if (filename.endsWith('.pdf')) {
        type = 'pdf';
      }

      return {
        type,
        filename,
        path: filePath,
        size: stats.size,
        viewerUrl: type === 'trace' 
          ? `/trace/${sessionName}/${filename}`
          : `/artifact/${sessionName}/${filename}`,
        createdAt: stats.birthtime.toISOString()
      };
    });

    res.json({ artifacts });
  } catch (error) {
    console.error('Error listing session artifacts:', error);
    res.status(500).json({ error: 'Failed to list artifacts' });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  console.error('Server error:', error);
  res.status(500).json({ error: 'Internal server error' });
});

// Start server
app.listen(port, '0.0.0.0', () => {
  console.log(`Playwright trace viewer service running on port ${port}`);
  console.log(`Artifacts directory: ${artifactsDir}`);
  console.log(`CORS origins: ${corsOptions.origin}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  process.exit(0);
});