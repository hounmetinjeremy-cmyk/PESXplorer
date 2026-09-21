const originalFetch = window.fetch;
window.fetch = async function(url, options) {
    if (url === 'players.json' || url === './players.json' || url.endsWith('/players.json')) {
        const response = await originalFetch('/api/players');
        if (!response.ok) {
            throw new Error(`Failed to load players (${response.status})`);
        }
        const decompressed = await new Response(
            response.body.pipeThrough(new DecompressionStream('gzip'))
        ).text();
        return new Response(decompressed, {
            headers: { 'Content-Type': 'application/json' }
        });
    }
    return originalFetch(url, options);
};
