// FE-9: production server. Serves the built React app and proxies /api and /ws to FastAPI. No business logic.
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { createProxyMiddleware } from 'http-proxy-middleware';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000';
const PORT = process.env.PORT || 3000;

const app = express();
const proxy = createProxyMiddleware(['/api', '/ws'], { target: BACKEND, changeOrigin: true, ws: true });
app.use(proxy);
app.use(express.static(path.join(__dirname, 'dist')));
app.get('*', (_req, res) => res.sendFile(path.join(__dirname, 'dist', 'index.html')));

const server = app.listen(PORT, () => console.log(`Frontend on http://localhost:${PORT} -> ${BACKEND}`));
server.on('upgrade', proxy.upgrade);
