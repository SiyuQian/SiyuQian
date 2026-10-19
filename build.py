"""Render the neofetch-style profile card and refresh README sections.

Run by .github/workflows/build.yml. Needs GITHUB_TOKEN and Pillow.
"""
import datetime as dt
import html
import json
import os
import re
import unicodedata
import urllib.request

from PIL import Image

USER = "SiyuQian"
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
W, H = 1000, 500
ART_COLS, ART_ROWS, ART_LH, ART_FONT = 96, 40, 7, 7
ART_X, ART_W = 24, 380
ART_Y = (H - ART_ROWS * ART_LH) // 2  # vertically centred
INFO_X, INFO_Y, INFO_LH, INFO_COLS = 430, 38, 21, 58
RAMP = "+*#%@"  # dense glyphs only: colour carries the picture

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", text="#c9d1d9", key="#ffa657",
                 value="#a5d6ff", dots="#484f58", accent="#3fb950"),
    "light": dict(bg="#f6f8fa", border="#d0d7de", text="#24292f", key="#953800",
                  value="#0a3069", dots="#afb8c1", accent="#1a7f37"),
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(first: 100, privacy: PUBLIC, ownerAffiliations: OWNER,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes { name description url pushedAt stargazerCount isFork isArchived }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]["user"]


def cols(s):
    """Monospace display width: CJK and emoji take two columns."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def uptime(since, today):
    months = (today.year - since.year) * 12 + today.month - since.month - (today.day < since.day)
    return f"{months // 12} years, {months % 12} months"


def art_rows():
    """Colored ASCII rows: list of [char_run, hex_color, start_col]."""
    im = Image.open(os.path.join(os.path.dirname(__file__), "cat.png")).convert("RGB")
    im = im.resize((ART_COLS, ART_ROWS), Image.LANCZOS)
    rows = []
    for y in range(ART_ROWS):
        runs = []
        for x in range(ART_COLS):
            r, g, b = im.getpixel((x, y))
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            ch = RAMP[min(len(RAMP) - 1, int(lum * len(RAMP)))]
            # brighten: the art always sits on a dark backdrop
            r, g, b = (int(255 * (c / 255) ** 0.6) for c in (r, g, b))
            color = "#%x%x%x" % (r >> 4, g >> 4, b >> 4)
            if runs and runs[-1][1] == color and runs[-1][2] + len(runs[-1][0]) == x:
                runs[-1][0] += ch
            else:
                runs.append([ch, color, x])
        rows.append(runs)
    return rows


def info_lines(u, today):
    repos = [r for r in u["repositories"]["nodes"] if not r["isFork"]]
    stars = sum(r["stargazerCount"] for r in repos)
    since = dt.date.fromisoformat(u["createdAt"][:10])
    contribs = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    # ("title", text) | ("kv", key, value) | ("blank",)
    return [
        ("title", "siyu@aotearoa"),
        ("kv", "OS", "macOS, Linux (OrbStack)"),
        ("kv", "Host", "Forsyth Barr"),
        ("kv", "Kernel", "Senior Software Engineer"),
        ("kv", "Uptime", uptime(since, today) + " on GitHub"),
        ("kv", "Shell", "zsh"),
        ("kv", "Agents", "Claude Code, bb, Orca"),
        ("blank",),
        ("kv", "Languages.Code", "Go, TypeScript, Rust, Python"),
        ("kv", "Languages.Real", "中文, English"),
        ("blank",),
        ("kv", "Homelab", "3 Macs on Tailscale"),
        ("kv", "Homelab.CI", "16 self-hosted GitHub runners"),
        ("kv", "Learning", "quant research, finance basics"),
        ("kv", "Avatar", "a cat wearing a burger"),
        ("blank",),
        ("title", "GitHub Stats"),
        ("kv", "Public repos", str(u["repositories"]["totalCount"])),
        ("kv", "Stars", str(stars)),
        ("kv", "Followers", str(u["followers"]["totalCount"])),
        ("kv", "Contributions (1y)", f"{contribs:,}"),
    ]


def render(u, theme, today):
    t = THEMES[theme]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}">',
        "<style>text,tspan{white-space:pre}</style>",
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["bg"]}" '
        f'stroke="{t["border"]}"/>',
    ]
    if theme == "light":  # keep the art on a dark "screen" so it reads the same
        out.append(f'<rect x="{ART_X - 10}" y="{ART_Y - 6}" width="{ART_W + 20}" '
                   f'height="{ART_ROWS * ART_LH + 18}" rx="8" fill="{THEMES["dark"]["bg"]}"/>')
    for i, runs in enumerate(art_rows()):
        y = ART_Y + (i + 1) * ART_LH
        # an x per glyph keeps the grid exact whatever monospace font the viewer has
        cell = ART_W / ART_COLS
        spans = "".join(
            '<tspan x="%s" fill="%s">%s</tspan>'
            % (" ".join(f"{ART_X + (c0 + j) * cell:.1f}" for j in range(len(s))), c, html.escape(s))
            for s, c, c0 in runs
        )
        out.append(f'<text y="{y}" font-size="{ART_FONT}">{spans}</text>')
    y = INFO_Y
    for line in info_lines(u, today):
        if line[0] == "title":
            rule = "—" * (INFO_COLS - len(line[1]) - 1)
            out.append(f'<text x="{INFO_X}" y="{y}" font-size="15" fill="{t["accent"]}" '
                       f'font-weight="bold">{html.escape(line[1])} '
                       f'<tspan fill="{t["dots"]}" font-weight="normal">{rule}</tspan></text>')
        elif line[0] == "kv":
            _, k, v = line
            dots = "." * max(2, INFO_COLS - cols(k) - cols(v) - 4)
            out.append(f'<text x="{INFO_X}" y="{y}" font-size="15" fill="{t["text"]}">'
                       f'<tspan fill="{t["key"]}">{html.escape(k)}</tspan>:'
                       f'<tspan fill="{t["dots"]}"> {dots} </tspan>'
                       f'<tspan fill="{t["value"]}">{html.escape(v)}</tspan></text>')
        y += INFO_LH
    out.append("</svg>")
    return "\n".join(out) + "\n"


def recent_md(u, n=5):
    repos = [r for r in u["repositories"]["nodes"]
             if not r["isFork"] and not r["isArchived"] and r["name"] != USER][:n]
    return "\n".join(
        f"- [**{r['name']}**]({r['url']}) — {r['description'] or 'no description yet'} "
        f"<sub>· pushed {r['pushedAt'][:10]}</sub>"
        for r in repos
    )


def replace_section(text, name, body):
    pattern = re.compile(rf"(<!-- {name} starts -->).*?(<!-- {name} ends -->)", re.S)
    return pattern.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(2), text)


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    u = fetch()
    today = dt.date.today()
    for theme in THEMES:
        with open(os.path.join(root, f"{theme}_mode.svg"), "w") as f:
            f.write(render(u, theme, today))
    readme = os.path.join(root, "README.md")
    with open(readme) as f:
        text = f.read()
    with open(readme, "w") as f:
        f.write(replace_section(text, "recent", recent_md(u)))


if __name__ == "__main__":
    main()
