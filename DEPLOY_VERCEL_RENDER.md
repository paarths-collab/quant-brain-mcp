# Deploy: Vercel (Frontend) + Render (Backend)

## 1) Deploy Backend on Render

1. Push this repo to GitHub.
2. In Render: New + -> Blueprint.
3. Select your repo. Render will detect `render.yaml`.
4. Create service.
5. In Render service -> Environment, set:
   - `CORS_ORIGINS=https://<your-vercel-domain>`
   - `FMP_API_KEY=...` (optional but recommended)
   - `FINNHUB_API_KEY=...` (optional but recommended)
   - Any other API keys you use.
6. Wait for deploy to finish and copy backend URL, e.g. `https://bloomberg-backend.onrender.com`.

Health URL:
- `https://<your-render-domain>/health`

## 2) Deploy Frontend on Vercel

1. In Vercel: Add New -> Project.
2. Import the same repo.
3. Set **Root Directory** to `ethena`.
4. Build settings:
   - Framework: Next.js
   - Build Command: `npm run build`
   - Output: default
5. Add environment variables in Vercel project:
   - `BACKEND_URL=https://<your-render-domain>`
   - `NEXT_PUBLIC_BACKEND_URL=https://<your-render-domain>`
   - `NEXT_PUBLIC_WS_URL=wss://<your-render-domain-without-https>/ws/live`
6. Deploy.

## 3) Validate

1. Open frontend Vercel URL.
2. Check API proxy path:
   - `https://<your-vercel-domain>/api/peers/compare/AAPL?limit=5`
3. Check backend directly:
   - `https://<your-render-domain>/health`
4. Test WebSocket-dependent features in UI.

## Notes

- Frontend uses Next rewrites in `ethena/next.config.js` to proxy `/api/*` and `/ws/*` to backend.
- If you change backend domain, update the 3 Vercel env vars and redeploy.
- Render free/starter plans may cold start after inactivity.
