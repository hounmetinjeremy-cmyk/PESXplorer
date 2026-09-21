# PESXplorer — Cloudflare Pages Setup

## Goal
Host PESXplorer on Cloudflare Pages despite `players.json` being ~95 MB, which exceeds Cloudflare Pages' 25 MiB per-file limit.

## How it works
1. `optimize.py` reads `players.json`, compresses it with `gzip`, and, if still too large, splits it into multiple `players.N.json.gz` files under 25 MiB each.
2. It patches `script.js` to load and decompress these files in the browser using `DecompressionStream`.
3. It writes a `_headers` file so Cloudflare Pages serves the `.gz` files with `Content-Encoding: gzip` and `Content-Type: application/json`.
4. It removes the original `players.json` from the `cloudflare-optimized` branch (kept on `main`).

## Run the optimizer locally
```bash
git clone https://github.com/hounmetinjeremy-cmyk/PESXplorer.git
cd PESXplorer
git checkout cloudflare-optimized
python3 optimize.py
```

## Run the optimizer via GitHub Actions
1. Push any change to the `cloudflare-optimized` branch, **or**
2. Go to **Actions → Optimize for Cloudflare Pages → Run workflow**.

## Deploy on Cloudflare Pages
1. In the Cloudflare dashboard, create a new Pages project.
2. Connect to GitHub → select `hounmetinjeremy-cmyk/PESXplorer`.
3. Set the branch to `cloudflare-optimized`.
4. Build settings:
   - **Framework preset:** None
   - **Build command:** `python3 optimize.py`
   - **Build output directory:** `/`
5. Save and deploy.

## Verify
Open the deployed URL and the browser console (F12). You should see:
- One or more `players.N.json.gz` requests, each under 25 MiB.
- HTTP 200 and `Content-Encoding: gzip`.
- A working player list after decompression.

## Browser support
`DecompressionStream('gzip')` works in all modern browsers (Chrome, Firefox, Edge, Safari). It does **not** work in Internet Explorer.
