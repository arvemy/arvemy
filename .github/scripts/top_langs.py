"""Render a compact "Most Used Languages" card across owned and organization repos.

Reads GITHUB_TOKEN from the environment and writes the SVG to the path given as
the first argument. Styled to match the github-readme-stats tokyonight theme.
"""

import json
import os
import sys
import urllib.request
from html import escape

LANGS_COUNT = 8
EXCLUDE_LANGS = set()

QUERY = """
query($cursor: String) {
  viewer {
    repositories(
      affiliations: [OWNER, ORGANIZATION_MEMBER]
      ownerAffiliations: [OWNER, ORGANIZATION_MEMBER]
      isFork: false
      first: 100
      after: $cursor
    ) {
      pageInfo { hasNextPage endCursor }
      nodes {
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def graphql(token, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        body = json.load(res)
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["viewer"]["repositories"]


def fetch_languages(token):
    sizes, colors, cursor = {}, {}, None
    while True:
        page = graphql(token, {"cursor": cursor})
        for repo in page["nodes"]:
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                if name in EXCLUDE_LANGS:
                    continue
                sizes[name] = sizes.get(name, 0) + edge["size"]
                colors[name] = edge["node"]["color"] or "#858585"
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return sizes, colors


def render(sizes, colors):
    top = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:LANGS_COUNT]
    total = sum(size for _, size in top)
    rows = (len(top) + 1) // 2
    width, height = 300, 80 + rows * 25

    bar, x = [], 0.0
    for name, size in top:
        w = size / total * 250
        bar.append(f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="8" fill="{colors[name]}"/>')
        x += w

    items = []
    for i, (name, size) in enumerate(top):
        col, row = i % 2, i // 2
        items.append(
            f'<g transform="translate({col * 150}, {row * 25})">'
            f'<circle cx="5" cy="6" r="5" fill="{colors[name]}"/>'
            f'<text x="15" y="10" class="lang-name">{escape(name)} {size / total * 100:.2f}%</text>'
            "</g>"
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" role="img" aria-labelledby="title">
  <title id="title">Most Used Languages</title>
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #70a5fd; }}
    .lang-name {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #38bdae; }}
  </style>
  <rect x="0.5" y="0.5" rx="4.5" width="{width - 1}" height="{height - 1}" fill="#1a1b27"/>
  <text x="25" y="35" class="header">Most Used Languages</text>
  <g transform="translate(25, 55)">
    <mask id="bar-mask"><rect x="0" y="0" width="250" height="8" rx="5" fill="white"/></mask>
    <g mask="url(#bar-mask)">{"".join(bar)}</g>
    <g transform="translate(0, 25)">{"".join(items)}</g>
  </g>
</svg>
"""


def main():
    token = os.environ["GITHUB_TOKEN"]
    sizes, colors = fetch_languages(token)
    if not sizes:
        raise SystemExit("No language data returned; refusing to overwrite the card.")
    with open(sys.argv[1], "w") as f:
        f.write(render(sizes, colors))


if __name__ == "__main__":
    main()
