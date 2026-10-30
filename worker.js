// Zuban Daraz South Asian Proverbs API: single-file Cloudflare Worker, no dependencies.

const HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Content-Type": "application/json; charset=utf-8",
};
const CACHE = { "Cache-Control": "public, max-age=300" };

const json = (body, status = 200, extra = {}) =>
  new Response(JSON.stringify(body), { status, headers: { ...HEADERS, ...extra } });

// Only approved idioms, and only these fields, are ever exposed.
const FROM = "FROM entries WHERE status = 'approved' AND LOWER(pos) = 'idiom'";
const COLS = "id, word AS proverb, literal_definition AS translation, language, theme";

// ---- tiny Turso client over its HTTP API ----
const toArg = (v) =>
  typeof v === "number" ? { type: "integer", value: String(v) } : { type: "text", value: String(v) };

const fromCell = (c) => {
  if (!c || c.type === "null") return null;
  if (c.type === "integer" || c.type === "float") return Number(c.value);
  return c.value;
};

async function query(env, sql, args = []) {
  const base = env.TURSO_URL.replace(/^libsql:\/\//, "https://");
  const res = await fetch(`${base}/v2/pipeline`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.TURSO_AUTH_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      requests: [
        { type: "execute", stmt: { sql, args: args.map(toArg) } },
        { type: "close" },
      ],
    }),
  });
  if (!res.ok) throw new Error(`Turso HTTP ${res.status}`);
  const first = (await res.json()).results[0];
  if (first.type === "error") throw new Error(first.error.message);
  const { cols, rows } = first.response.result;
  return rows.map((r) => Object.fromEntries(cols.map((c, i) => [c.name, fromCell(r[i])])));
}

// ---- helpers ----
function buildFilters(p) {
  const where = [];
  const args = [];
  const language = (p.get("language") || "").trim();
  const theme = (p.get("theme") || "").trim();
  const q = (p.get("q") || "").trim();

  if (language) { where.push("LOWER(language) = LOWER(?)"); args.push(language); }
  if (theme) { where.push("LOWER(theme) = LOWER(?)"); args.push(theme); }
  if (q) {
    const like = `%${q.replace(/[\\%_]/g, (m) => "\\" + m)}%`; // escape LIKE wildcards
    where.push("(word LIKE ? ESCAPE '\\' OR literal_definition LIKE ? ESCAPE '\\')");
    args.push(like, like);
  }
  return { clause: where.length ? " AND " + where.join(" AND ") : "", args };
}

const shape = (r) => ({
  id: r.id,
  proverb: r.proverb,
  translation: r.translation ?? null,
  language: r.language,
  theme: r.theme ?? null,
});

const clampInt = (v, def, min, max) => {
  const n = parseInt(v, 10);
  return Number.isNaN(n) ? def : Math.min(Math.max(n, min), max);
};

// ---- routes ----
export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: HEADERS });
    if (request.method !== "GET") return json({ error: "Method not allowed" }, 405);

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const p = url.searchParams;

    try {
      if (path === "/") {
        return json({
          name: "Zuban Daraz Proverbs API",
          version: "v1",
          endpoints: {
            list: "/v1/proverbs?language=&theme=&q=&limit=20&offset=0",
            one: "/v1/proverbs/{id}",
            random: "/v1/proverbs/random?language=&theme=",
            languages: "/v1/languages",
            themes: "/v1/themes",
          },
        }, 200, CACHE);
      }

      if (path === "/v1/proverbs") {
        const { clause, args } = buildFilters(p);
        const limit = clampInt(p.get("limit"), 20, 1, 100);
        const offset = clampInt(p.get("offset"), 0, 0, 1e9);
        const [count, rows] = await Promise.all([
          query(env, `SELECT COUNT(*) AS n ${FROM}${clause}`, args),
          query(env, `SELECT ${COLS} ${FROM}${clause} ORDER BY id LIMIT ? OFFSET ?`, [...args, limit, offset]),
        ]);
        return json({ data: rows.map(shape), meta: { total: count[0].n, limit, offset } }, 200, CACHE);
      }

      if (path === "/v1/proverbs/random") {
        const { clause, args } = buildFilters(p);
        const rows = await query(env, `SELECT ${COLS} ${FROM}${clause} ORDER BY RANDOM() LIMIT 1`, args);
        if (!rows.length) return json({ error: "No proverbs match" }, 404);
        return json({ data: shape(rows[0]) }, 200, { "Cache-Control": "no-store" });
      }

      const one = path.match(/^\/v1\/proverbs\/(\d+)$/);
      if (one) {
        const rows = await query(env, `SELECT ${COLS} ${FROM} AND id = ?`, [parseInt(one[1], 10)]);
        if (!rows.length) return json({ error: "Not found" }, 404);
        return json({ data: shape(rows[0]) }, 200, CACHE);
      }

      if (path === "/v1/languages") {
        const rows = await query(env, `SELECT language AS name, COUNT(*) AS count ${FROM} GROUP BY language ORDER BY count DESC`);
        return json({ data: rows }, 200, CACHE);
      }

      if (path === "/v1/themes") {
        const rows = await query(env, `SELECT theme AS name, COUNT(*) AS count ${FROM} AND theme IS NOT NULL GROUP BY theme ORDER BY count DESC`);
        return json({ data: rows }, 200, CACHE);
      }

      return json({ error: "Not found" }, 404);
    } catch (err) {
      console.error(err);
      return json({ error: "Internal server error" }, 500);
    }
  },
};
