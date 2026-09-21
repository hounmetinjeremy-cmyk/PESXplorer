export async function onRequestGet(context) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  if (context.request.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  const GITHUB_RAW = 'https://raw.githubusercontent.com/hounmetinjeremy-cmyk/PESXplorer/main/players.json';
  const CACHE_TTL = 86400;

  try {
    const response = await fetch(GITHUB_RAW, { cf: { cacheTtl: CACHE_TTL } });
    if (!response.ok) {
      return new Response('Failed to load players data: ' + response.status, {
        status: 502,
        headers: corsHeaders,
      });
    }

    const jsonText = await response.text();
    const compressed = await compress(jsonText);

    return new Response(compressed, {
      status: 200,
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json',
        'Content-Encoding': 'gzip',
        'Cache-Control': 'public, max-age=' + CACHE_TTL,
        'Vary': 'Accept-Encoding',
      },
    });
  } catch (err) {
    return new Response('Error: ' + err.message, { status: 500, headers: corsHeaders });
  }
}

async function compress(text) {
  const encoder = new TextEncoder();
  const input = encoder.encode(text);
  const cs = new CompressionStream('gzip');
  const writer = cs.writable.getWriter();
  writer.write(input);
  writer.close();
  return new Response(cs.readable).arrayBuffer();
}
