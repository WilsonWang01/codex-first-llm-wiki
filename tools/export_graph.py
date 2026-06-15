#!/usr/bin/env python3
"""Export an Obsidian-friendly wiki graph from link-index data."""

from __future__ import annotations

import argparse
import json
import sys

from wiki_common import META, dump_json, load_json, now_iso, write_text
from lint_links import analyze


def build_graph() -> dict:
    link_index = analyze()
    nodes = []
    edges = []
    for path, page in sorted(link_index["pages"].items()):
        nodes.append({"id": path, "title": page["title"]})
        for target in page["outbound"]:
            edges.append({"source": path, "target": target})
    return {
        "schema_version": 1,
        "built_at": now_iso(),
        "nodes": nodes,
        "edges": sorted(edges, key=lambda item: (item["source"], item["target"])),
    }


def render_html(graph: dict) -> str:
    payload = json.dumps(graph, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Codex Wiki Graph</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; }}
    pre {{ white-space: pre-wrap; background: #f6f8fa; padding: 16px; border-radius: 6px; }}
    li {{ margin: 4px 0; }}
  </style>
</head>
<body>
  <h1>Codex Wiki Graph</h1>
  <p>Nodes: {len(graph['nodes'])}. Edges: {len(graph['edges'])}.</p>
  <h2>Edges</h2>
  <ul>
    {''.join(f"<li><code>{edge['source']}</code> -> <code>{edge['target']}</code></li>" for edge in graph['edges'])}
  </ul>
  <h2>Raw Graph JSON</h2>
  <pre id="graph"></pre>
  <script>
    document.getElementById('graph').textContent = JSON.stringify({payload}, null, 2);
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", action="store_true", help="Also write meta/graph.html.")
    parser.add_argument("--json", action="store_true", help="Print graph JSON.")
    args = parser.parse_args()

    graph = build_graph()
    dump_json(META / "graph.json", graph)
    if args.html:
        write_text(META / "graph.html", render_html(graph))
    if args.json:
        print(json.dumps(graph, ensure_ascii=False, indent=2))
    else:
        print(f"graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
