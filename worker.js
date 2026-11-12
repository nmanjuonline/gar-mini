export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/api/sync') {
      if (request.method === 'OPTIONS') {
        return new Response(null, {
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
          }
        });
      }
      if (request.method === 'POST') {
        if (env.GITHUB_TOKEN) {
          try {
            const ghRes = await fetch('https://api.github.com/repos/nmanjuonline/gar-mini/actions/workflows/scheduled-refresh.yml/dispatches', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
                'Accept': 'application/vnd.github+json',
                'User-Agent': 'Garmini-Worker',
                'X-GitHub-Api-Version': '2022-11-28'
              },
              body: JSON.stringify({ ref: 'main' })
            });
            if (ghRes.ok || ghRes.status === 204) {
              return new Response(JSON.stringify({
                success: true,
                message: 'GitHub Actions sync triggered! Data will refresh in ~1-2 minutes.'
              }), {
                headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
              });
            }
          } catch (e) {
            // Fall through to guidance
          }
        }
        return new Response(JSON.stringify({
          success: false,
          actionsUrl: 'https://github.com/nmanjuonline/gar-mini/actions/workflows/scheduled-refresh.yml',
          message: 'Cloudflare Worker is in static mode. Trigger manual sync via GitHub Actions or run locally.'
        }), {
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
        });
      }
    }

    return env.ASSETS.fetch(request);
  }
};
