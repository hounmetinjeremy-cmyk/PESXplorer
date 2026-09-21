export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const id = url.searchParams.get('id');
  const search = url.searchParams.get('search');
  const page = parseInt(url.searchParams.get('page') || '1', 10);
  const limit = parseInt(url.searchParams.get('limit') || '50', 10);

  try {
    if (!env.DB) {
      return Response.json({ error: 'Database not configured' }, { status: 500 });
    }

    if (id) {
      const player = await env.DB.prepare('SELECT * FROM players WHERE id = ?').bind(id).first();
      return Response.json(player || { error: 'Not found' });
    }

    let query = 'SELECT * FROM players';
    let countQuery = 'SELECT COUNT(*) as total FROM players';
    let params = [];

    if (search) {
      query += ' WHERE name LIKE ? OR team LIKE ? OR position LIKE ?';
      countQuery += ' WHERE name LIKE ? OR team LIKE ? OR position LIKE ?';
      const like = `%${search}%`;
      params = [like, like, like];
    }

    query += ` ORDER BY overall DESC LIMIT ? OFFSET ?`;

    const { results: players } = await env.DB.prepare(query).bind(...params, limit, (page - 1) * limit).all();
    const { results: countResult } = await env.DB.prepare(countQuery).bind(...params).all();
    const total = countResult[0]?.total || 0;

    return Response.json({
      players,
      pagination: { page, limit, total, pages: Math.ceil(total / limit) }
    });
  } catch (err) {
    return Response.json({ error: err.message }, { status: 500 });
  }
}
