export async function onRequestGet(context) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  if (context.request.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    // Lire players.json depuis le bucket R2 lié à PLAYERS_DATA
    const object = await context.env.PLAYERS_DATA.get('players.json');

    if (!object) {
      return new Response('players.json not found in R2', {
        status: 404,
        headers: corsHeaders,
      });
    }

    const headers = new Headers();
    object.writeHttpMetadata(headers);
    headers.set('Access-Control-Allow-Origin', '*');
    headers.set('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS');
    headers.set('Access-Control-Allow-Headers', 'Content-Type');
    headers.set('Content-Type', 'application/json');
    headers.set('Cache-Control', 'public, max-age=86400');

    return new Response(object.body, { headers });
  } catch (err) {
    return new Response('Error: ' + err.message, {
      status: 500,
      headers: corsHeaders,
    });
  }
}
