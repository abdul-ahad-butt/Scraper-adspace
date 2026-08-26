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

    if (url.pathname === "/api/image") {
      const targetUrl = url.searchParams.get("url");
      if (!targetUrl) return new Response("Missing url parameter", { status: 400, headers: corsHeaders });

      try {
        const imageResponse = await fetch(targetUrl, {
          headers: {
            "Referer": "https://www.adbuq.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
          }
        });

        const headers = new Headers(imageResponse.headers);
        headers.set("Access-Control-Allow-Origin", "*");

        return new Response(imageResponse.body, {
          status: imageResponse.status,
          headers: headers
        });
      } catch (e) {
        return new Response("Error fetching image", { status: 500, headers: corsHeaders });
      }
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders });
  },
};
