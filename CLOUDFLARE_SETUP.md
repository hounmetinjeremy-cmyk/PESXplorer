# PESXplorer — Cloudflare Pages Setup

## Goal
Host PESXplorer on Cloudflare Pages despite `players.json` being ~95 MB, which exceeds Cloudflare Pages' 25 MiB per-file limit.

## How it works
1. `optimize.py` reads `players.json`, compresses it with `gzip`. If still larger than 25 MiB, it splits it into several `players.N.json.gz` chunks, each under 25 MiB.
2. It patches `script.js` so the browser decompresses and loads those chunks with `DecompressionStream`.
3. It writes `_headers` for Cloudflare Pages so `.gz` files are served with `Content-Encoding: gzip`.
4. The original `players.json` is removed from the deployment branch.

## Method A — Fully automated via GitHub Actions (recommended)
1. Push any change to the `main` branch (or edit and commit `players.json`).
2. The workflow `.github/workflows/optimize-cloudflare.yml` runs automatically.
3. It creates/updates the `cloudflare-optimized` branch.

## Method B — Local run
```bash
git clone https://github.com/hounmetinjeremy-cmyk/PESXplorer.git
cd PESXplorer
python3 optimize.py
git checkout -B cloudflare-optimized
git add -A
git commit -m "Optimize for Cloudflare Pages"
git push origin cloudflare-optimized --force
```

## Deploy on Cloudflare Pages
1. In Cloudflare dashboard → Pages → Create a project.
2. Connect GitHub → select `hounmetinjeremy-cmyk/PESXplorer`.
3. Branch: `cloudflare-optimized`.
4. Build settings:
   - Framework preset: **None**
   - Build command: *(empty)*
   - Build output directory: `/`
5. Save and deploy.

## Verify
Open the deployed site, press F12 → Network:
- `players.json.gz` (or several `players.N.json.gz`) returned with HTTP 200.
- `Content-Encoding: gzip` present.
- Player list loads after decompression.
