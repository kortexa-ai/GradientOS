---
name: vercel-next-deploy
description: Deploy and manage this Next.js app on Vercel (project linking, env vars, preview/prod, domains). Use when the user mentions Vercel, deployment, environment variables, previews, or domains.
---

# Vercel deploy (Next.js)

## Quick checklist (before deploying)

- `npm run lint`
- `npm run build`
- No secrets committed (env vars belong in Vercel and `.env.local`)

## Deploy via Vercel dashboard (recommended)

1. Import the repo in Vercel.
2. Framework preset: **Next.js** (auto-detected).
3. Install command: `npm install` (default).
4. Build command: `npm run build` (default).
5. Output: leave default (Next.js uses `.next`).
6. Add environment variables:
   - Vercel → Project → Settings → Environment Variables
   - Set values per environment (Development / Preview / Production)

## Deploy via CLI (optional)

- First deploy: `npx vercel`
- Promote to production: `npx vercel --prod`

## Common fixes

- If builds fail due to missing env vars, add them in Vercel settings and redeploy.
- Don’t add `vercel.json` unless you need custom rewrites/headers/cron jobs.

