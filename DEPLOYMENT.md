# Deployment — Buy The Rumour

Frontend (Next.js) → **Vercel**. Backend (FastAPI) → **Render**.

**Live now (verified 2026-07-14):**
- Frontend: <https://pdt-hackathon.vercel.app>
- Backend: <https://pdt-hackathon.onrender.com> (`/api/health` → `{"status":"ok",...}`)

Both auto-redeploy on push to `main`. The URLs below are the real ones; the
Render service is named `pdt-hackathon` (its subdomain), and the Vercel project
resolves to `pdt-hackathon.vercel.app`. Keep these consistent — the frontend
bakes the backend URL at build time, so a mismatch silently breaks the app.

The two must know each other's URLs, so deploy in this order and wire them at
the end. `NEXT_PUBLIC_API_BASE_URL` is **baked into the frontend at build time**,
so it must be set on Vercel *before* the frontend build runs.

## 1. Backend → Render

1. Render dashboard → **New → Blueprint** → connect `javaxhaskell/PDT-Hackathon`.
   Render reads [`render.yaml`](render.yaml) and creates the `pdt-hackathon`
   web service (root dir `backend`, `uvicorn app.api.main:app`).
2. When prompted, set the two secret env vars:
   - `DEEPSEEK_API_KEY` — your DeepSeek key (optional; blank = quant only, AI lens
     shows "not configured").
   - `CORS_ORIGINS` — leave blank for now; you'll fill it in step 3.
3. Deploy. The service URL is `https://pdt-hackathon.onrender.com`.
   Verify: open `<url>/api/health` → `{"status":"ok",...}`.

## 2. Frontend → Vercel

1. Vercel → **Add New → Project** → import `javaxhaskell/PDT-Hackathon`.
2. **Root Directory → `frontend`** (required — the repo root has an unrelated
   `package.json`; Vercel must build from `frontend/`). Framework auto-detects as
   Next.js.
3. Add env var **`NEXT_PUBLIC_API_BASE_URL`** = the Render URL from step 1
   (`https://pdt-hackathon.onrender.com`, no trailing slash).
4. Deploy. The Vercel URL is `https://pdt-hackathon.vercel.app`.

## 3. Wire CORS back to the backend

1. Render → the service → **Environment** → set `CORS_ORIGINS` to the Vercel URL
   (`https://pdt-hackathon.vercel.app`, no trailing slash). Add any custom
   domains too, comma-separated.
2. Render redeploys. Done.

## Notes

- **Demo mode always works** (recorded fixtures: RCL/CCL, ALL/TRV). **Live mode**
  depends on Yahoo Finance, which can rate-limit or block datacenter IPs — if Live
  is flaky in prod, that's why; Demo is the reliable path for a live demo.
- Render's **free** web service cold-starts after ~15 min idle (first request is
  slow). Hit it once before demoing.
- Redeploys are automatic on push to `main` (`autoDeploy: true` / Vercel default).
- No secrets are committed; `backend/.env` is gitignored. Env vars are set in each
  platform's dashboard.
