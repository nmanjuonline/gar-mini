const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const PORT = 3000;
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json',
  '.webmanifest': 'application/manifest+json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.css': 'text/css'
};

let isSyncing = false;

const server = http.createServer((req, res) => {
  let reqPath = req.url.split('?')[0];

  // API endpoint for manual sync
  if (reqPath === '/api/sync') {
    if (req.method === 'OPTIONS') {
      res.writeHead(204, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      });
      return res.end();
    }

    if (req.method === 'POST') {
      if (isSyncing) {
        res.writeHead(409, {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        });
        return res.end(JSON.stringify({ success: false, error: 'A sync is already in progress.' }));
      }

      isSyncing = true;
      const py = process.platform === 'win32' ? 'python' : 'python3';
      const cmd = `${py} pull.py --activities-only && ${py} build.py`;

      console.log(`[Sync] Running: ${cmd}`);
      exec(cmd, { cwd: __dirname, timeout: 120000 }, (err, stdout, stderr) => {
        isSyncing = false;
        const output = (stderr || stdout || '').trim();
        if (err) {
          console.error('[Sync] Error:', output || err.message);
          res.writeHead(500, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          });
          return res.end(JSON.stringify({
            success: false,
            error: output || err.message
          }));
        }

        console.log('[Sync] Success! Activities synced and dashboard rebuilt.');
        res.writeHead(200, {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        });
        return res.end(JSON.stringify({
          success: true,
          message: 'Activities synced successfully! Dashboard updated.'
        }));
      });
      return;
    }
  }

  if (reqPath === '/' || reqPath === '') reqPath = '/index.html';
  
  let filePath = path.join(__dirname, reqPath);
  if (!fs.existsSync(filePath)) {
    filePath = path.join(__dirname, 'site', reqPath);
  }
  
  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Access-Control-Allow-Origin': '*'
    });
    fs.createReadStream(filePath).pipe(res);
  } else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Garmini dev server listening on port ${PORT}`);
});
