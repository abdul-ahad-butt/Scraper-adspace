import type { D1Database } from "@cloudflare/workers-types";

export interface Env {
  DB: D1Database;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Add CORS headers so the PyScript frontend can fetch data
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    if (url.pathname === "/api/billboards") {
      const { results } = await env.DB.prepare("SELECT * FROM billboards").all();
      return new Response(JSON.stringify(results), {
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders
        }
      });
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders });
  },
};
