#!/usr/bin/env node
/* eslint-disable no-console */

import process from "node:process";

function usage(exitCode = 0) {
  console.error(
    [
      "Usage:",
      '  brave_search.mjs "<query>" [--count N] [--offset N] [--type web|news|images|videos]',
      "",
      "Env:",
      "  BRAVE_API_KEY   (required)",
    ].join("\n"),
  );
  process.exit(exitCode);
}

function parseArgs(argv) {
  const args = { query: null, count: 10, offset: 0, type: "web" };

  const positionals = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") usage(0);
    if (!a.startsWith("--")) {
      positionals.push(a);
      continue;
    }
    const key = a.slice(2);
    if (key === "count") {
      const v = argv[++i];
      if (!v) usage(2);
      args.count = Number(v);
    } else if (key === "offset") {
      const v = argv[++i];
      if (!v) usage(2);
      args.offset = Number(v);
    } else if (key === "type") {
      const v = argv[++i];
      if (!v) usage(2);
      args.type = v;
    } else {
      console.error(`Unknown flag: ${a}`);
      usage(2);
    }
  }

  if (positionals.length === 0) usage(2);
  if (positionals.length === 1 && (positionals[0] === "--help" || positionals[0] === "-h")) usage(0);
  args.query = positionals.join(" ");
  if (!Number.isFinite(args.count) || args.count < 1 || args.count > 20) {
    console.error("--count must be 1..20");
    process.exit(2);
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  const apiKey = process.env.BRAVE_API_KEY;
  if (!apiKey) {
    console.error("Missing BRAVE_API_KEY in environment.");
    usage(2);
  }

  // Build URL with query parameters
  const params = new URLSearchParams();
  params.set("q", args.query);
  params.set("count", String(args.count));
  params.set("offset", String(args.offset));
  
  const url = `https://api.search.brave.com/res/v1/${args.type}/search?${params.toString()}`;

  const res = await fetch(url, {
    method: "GET",
    headers: {
      "X-Subscription-Token": apiKey,
      "Accept": "application/json",
    },
  });

  const text = await res.text();
  if (!res.ok) {
    console.error(`Brave API error (${res.status}): ${text}`);
    process.exit(1);
  }

  // Parse and format output similar to exa-search
  try {
    const data = JSON.parse(text);
    const results = [];
    
    if (data.web && data.web.results) {
      for (const r of data.web.results) {
        results.push({
          title: r.title || "",
          url: r.url || "",
          snippet: r.description || "",
        });
      }
    }
    
    // Output in similar format to exa-search
    const output = {
      query: args.query,
      results: results,
      _meta: {
        count: results.length,
        type: args.type,
      }
    };
    process.stdout.write(JSON.stringify(output, null, 2));
  } catch (e) {
    // Fallback: output raw if parsing fails
    process.stdout.write(text);
  }
}

main().catch((err) => {
  console.error(err?.stack || String(err));
  process.exit(1);
});
