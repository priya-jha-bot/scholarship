# Scholarship frontend

    npm install
    npm run mock     # terminal 1  -> fake API on :4010
    npm run dev      # terminal 2  -> app on http://localhost:5173

Logins (password `password123`): student@example.com, admin@example.com, reviewer@example.com

Real backend: edit `.env` -> `VITE_PROXY_TARGET=http://localhost:8000`, restart `npm run dev`.
Production: `npm run build` then `npm start` (Express serves `dist/` and proxies /api and /ws to BACKEND_URL).
