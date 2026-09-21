#!/usr/bin/env python3
"""
Optimizer for Cloudflare Pages.

Reads players.json, gzip-compresses it (and optionally splits it if > 25 MiB),
patches script.js to load the compressed chunks via DecompressionStream,
and writes the _headers file required by Cloudflare Pages.
"""
import gzip
import json
import math
import os
import re

MAX_COMPRESSED_BYTES = 25 * 1024 * 1024
INPUT = "players.json"


def load_players():
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("players.json must be a JSON list")
    return data


def compressed_size(text_bytes):
    return len(gzip.compress(text_bytes, compresslevel=9))


def write_single(players):
    text_bytes = json.dumps(players).encode("utf-8")
    if compressed_size(text_bytes) > MAX_COMPRESSED_BYTES:
        return None
    with gzip.open("players.json.gz", "wb", compresslevel=9) as f:
        f.write(text_bytes)
    return ["players.json.gz"]


def write_chunks(players, target_bytes):
    lo, hi = 1, len(players)
    best_size = 1
    while lo <= hi:
        mid = (lo + hi) // 2
        sample = players[:mid]
        size = compressed_size(json.dumps(sample).encode("utf-8"))
        if size <= target_bytes:
            best_size = mid
            lo = mid + 1
        else:
            hi = mid - 1

    files = []
    per_chunk = max(1, best_size)
    chunk_count = math.ceil(len(players) / per_chunk)
    for i in range(chunk_count):
        chunk = players[i * per_chunk : (i + 1) * per_chunk]
        filename = f"players.{i + 1}.json.gz"
        with gzip.open(filename, "wt", encoding="utf-8", compresslevel=9) as f:
            json.dump(chunk, f)
        files.append(filename)
    return files


def patch_script_js(files):
    with open("script.js", "r", encoding="utf-8") as f:
        text = f.read()

    loader = f"""
    const DATA_FILES = {files};

    async function decompressGzip(url) {{
        const response = await fetch(url);
        if (!response.ok) {{
            throw new Error(`Failed to load ${{url}} (Error: ${{response.status}})`);
        }}
        const compressed = await response.arrayBuffer();
        const decompressed = await new Response(
            new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))
        ).text();
        return JSON.parse(decompressed);
    }}

    async function loadAllPlayers() {{
        const chunks = [];
        for (const url of DATA_FILES) {{
            chunks.push(await decompressGzip(url));
        }}
        return chunks.flat();
    }}
"""
    old_block = """const response = await fetch('players.json');
            if (!response.ok) {
                throw new Error(`Failed to load players.json (Error: ${response.status})`);
            }
            allPlayers = await response.json();"""

    new_block = "allPlayers = await loadAllPlayers();"

    if old_block in text:
        text = text.replace(old_block, new_block)
    else:
        # Fallback: search any bare fetch('players.json') line
        text = re.sub(r"fetch\s*\(\s*['\"`]players\.json['\"`]\s*\)(?:\.json\(\)|[\s\S]{0,80}?\.json\(\))", "await loadAllPlayers()", text)
        text = text.replace("'players.json'", "url").replace('"players.json"', "url")

    opener = "document.addEventListener('DOMContentLoaded', () => {"
    idx = text.find(opener)
    if idx != -1 and "decompressGzip" not in text:
        text = text[: idx + len(opener)] + loader + text[idx + len(opener) :]

    with open("script.js", "w", encoding="utf-8") as f:
        f.write(text)


def write_headers(files):
    with open("_headers", "w", encoding="utf-8") as f:
        for path in files:
            f.write(f"/{path}\n")
            f.write("  Content-Encoding: gzip\n")
            f.write("  Content-Type: application/json\n")
            f.write("  Cache-Control: public, max-age=86400\n\n")


def main():
    players = load_players()
    print(f"Loaded {len(players)} players")

    files = write_single(players)
    if files:
        file_size = os.path.getsize(files[0]) / 1024 / 1024
        print(f"Created {files[0]} ({file_size:.2f} MiB)")
    else:
        files = write_chunks(players, int(MAX_COMPRESSED_BYTES * 0.95))
        print(f"Created {len(files)} chunks under 25 MiB each")

    patch_script_js(files)
    write_headers(files)

    if os.path.exists(INPUT):
        os.remove(INPUT)
        print(f"Removed original {INPUT}")

    print("Optimization complete.")


if __name__ == "__main__":
    main()
