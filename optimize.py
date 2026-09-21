#!/usr/bin/env python3
"""
Optimizer for Cloudflare Pages.
This script:
  1. Reads players.json
  2. Compresses it as players.json.gz (and optionally splits if > 25 MiB)
  3. Patches script.js to load the .gz data via DecompressionStream
  4. Generates _headers for Cloudflare Pages
  5. Removes the original players.json if requested (default: keep it in repo, remove from deploy by using .cfignore / _headers)

Max file size on Cloudflare Pages: 25 MiB per asset.
"""
import gzip
import json
import math
import os
import re
import sys

MAX_COMPRESSED_BYTES = 25 * 1024 * 1024
INPUT = "players.json"


def compressed_size(data_bytes: bytes) -> int:
    return len(gzip.compress(data_bytes, compresslevel=9))


def load_players():
    print(f"Loading {INPUT}...")
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("players.json must be a list of players")
    return data


def choose_chunk_count(players, max_compressed=MAX_COMPRESSED_BYTES):
    full = json.dumps(players).encode("utf-8")
    n = 1
    while True:
        per = math.ceil(len(players) / n)
        sample = players[:per]
        size = compressed_size(json.dumps(sample).encode("utf-8"))
        print(f"  {n} chunk(s) -> ~{size / 1024 / 1024:.2f} MiB each")
        if size <= max_compressed:
            # Ensure next chunk would still fit
            if n == 1:
                return 1
            return n
        n += 1
        if n > 200:
            raise RuntimeError("Cannot compress players.json below Cloudflare Pages limit even with many chunks")


def write_chunks(players, chunk_count):
    files = []
    per = math.ceil(len(players) / chunk_count)
    for i in range(chunk_count):
        chunk = players[i * per : (i + 1) * per]
        fname = f"players.{i + 1}.json.gz"
        with gzip.open(fname, "wt", encoding="utf-8", compresslevel=9) as f:
            json.dump(chunk, f)
        files.append(fname)
        print(f"Wrote {fname}: {len(chunk)} players, {os.path.getsize(fname) / 1024 / 1024:.2f} MiB")
    return files


def patch_script_js(files):
    urls = json.dumps(files)
    loader = f"""
    const DATA_FILES = {urls};

    async function loadPlayersGzip() {{
        const chunks = [];
        for (const url of DATA_FILES) {{
            const res = await fetch(url);
            if (!res.ok) throw new Error(`Failed to load ${{url}}: ${{res.status}}`);
            const compressed = await res.arrayBuffer();
            const decompressed = await new Response(
                new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))
            ).text();
            chunks.push(JSON.parse(decompressed));
        }}
        return chunks.flat();
    }}
"""
    with open("script.js", "r", encoding="utf-8") as f:
        text = f.read()

    # Find the existing init() or players.json fetch
    if "players.json" not in text:
        raise ValueError("Could not find 'players.json' reference in script.js")

    # Normalize old fetch block
    # Match variants: fetch('players.json'), fetch("players.json"), fetch(`players.json`)
    pattern = re.compile(
        r"(?:(?:const|let|var)\s+\w+\s*=\s*)?(?:await\s+)?fetch\s*\(\s*['\"`]players\.json['\"`]\s*\)(?:[\s\S]{0,200}?\)\.json\(\)|[\s\S]{0,300}?\.then\s*\([^)]*\)\s*(?:\.then\s*\([^)]*\))?)",
        re.DOTALL,
    )

    match = pattern.search(text)
    if not match:
        # Fallback: just substitute bare fetch calls
        print("Warning: could not match full fetch block; doing simple string substitution")
        text = text.replace("'players.json'", "url").replace('"players.json"', "url").replace("`players.json`", "url")
    else:
        text = text[: match.start()] + "allPlayers = await loadPlayersGzip();" + text[match.end() :]

    # Inject loader after DOMContentLoaded opener if not already there
    if "loadPlayersGzip" not in text:
        opener = "document.addEventListener('DOMContentLoaded', () => {"
        idx = text.find(opener)
        if idx != -1:
            text = text[: idx + len(opener)] + loader + text[idx + len(opener) :]
        else:
            text = loader + text

    with open("script.js", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched script.js")


def write_headers(files):
    lines = []
    for f in files:
        lines.append(f"/{f}")
        lines.append("  Content-Encoding: gzip")
        lines.append("  Content-Type: application/json")
        lines.append("  Cache-Control: public, max-age=86400")
        lines.append("")
    with open("_headers", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Wrote _headers")


def write_manifest(files):
    manifest = {"chunks": files}
    with open("players.chunks.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    print("Wrote players.chunks.json")


def main():
    players = load_players()
    print(f"Total players: {len(players)}")

    # Try single file first
    full_bytes = json.dumps(players).encode("utf-8")
    single_size = compressed_size(full_bytes)
    print(f"players.json.gz single file size: ~{single_size / 1024 / 1024:.2f} MiB")

    if single_size <= MAX_COMPRESSED_BYTES:
        files = ["players.json.gz"]
        with gzip.open("players.json.gz", "wt", encoding="utf-8", compresslevel=9) as f:
            json.dump(players, f)
        print(f"Wrote players.json.gz ({os.path.getsize('players.json.gz') / 1024 / 1024:.2f} MiB)")
    else:
        chunk_count = choose_chunk_count(players)
        files = write_chunks(players, chunk_count)

    patch_script_js(files)
    write_headers(files)
    write_manifest(files)

    # Optional: remove original players.json from deploy by renaming it out? No, keep in repo.
    # Instead, use .cfignore for Pages? Cloudflare Pages uses .gitignore-style only if we configure.
    # Simpler: we will delete it in this branch.
    if os.path.exists(INPUT):
        os.remove(INPUT)
        print(f"Removed original {INPUT} from this branch (kept in main branch)")

    print("\nOptimization complete. Ready for Cloudflare Pages.")


if __name__ == "__main__":
    main()
