#!/usr/bin/env python3
"""Gera assets/hello.svg, o cartão estilo terminal do perfil.

Os textos fixos ficam em CONFIG. Os números (repos, stars, contribuições,
seguidores) vêm da API do GitHub quando GH_TOKEN está definido; sem token
o cartão mostra "-" no lugar dos números.
"""
import json
import os
import urllib.request
from html import escape

CONFIG = {
    "login": "oliveiraluizmiguel57-blip",
    "user": "luiz@cin",
    "info": [
        ("curso", "sistemas de informação"),
        ("sem", "3º, CIn-UFPE"),
        ("foco", "full-stack"),
        ("stack", "c++, react, node"),
        ("extra", "cibersegurança"),
    ],
    "status": [
        ("estágio", "aberto"),
        ("local", "recife, pe"),
        ("estudando", "arquitetura limpa"),
    ],
    "projects": [("drwxr-xr-x", "SmartHome.cin/"), ("drwxr-xr-x", "CliniDesk/")],
}

BG, CARD, BORDER = "#E4E9F2", "#F7F9FC", "#CBD5E6"
INK, MUTED, ACCENT = "#0B192C", "#5B6B85", "#0052D4"
MONO = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"

# fonte bitmap 5x7 só para a palavra "hello" (x = pixel aceso)
GLYPHS = {
    "h": ["X....", "X....", "X.XX.", "XX..X", "X...X", "X...X", "X...X"],
    "e": [".....", ".....", ".XXX.", "X...X", "XXXXX", "X....", ".XXXX"],
    "l": ["X", "X", "X", "X", "X", "X", "X"],
    "o": [".....", ".....", ".XXX.", "X...X", "X...X", "X...X", ".XXX."],
}


def _request(url, token, body=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_stats():
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("GH_TOKEN ausente; números ficam como '-'")
        return {}
    login = CONFIG["login"]

    # 1) GraphQL: traz tudo, inclusive contribuições
    query = """query($login:String!){user(login:$login){
      followers{totalCount}
      repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC){totalCount nodes{stargazerCount}}
      contributionsCollection{contributionCalendar{totalContributions}}}}"""
    try:
        resp = _request("https://api.github.com/graphql", token,
                        {"query": query, "variables": {"login": login}})
        u = (resp.get("data") or {}).get("user")
        if u:
            return {
                "repos": u["repositories"]["totalCount"],
                "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
                "contribuições": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
                "seguidores": u["followers"]["totalCount"],
            }
        print("Erro da API (GraphQL):", resp.get("errors") or resp)
    except Exception as e:
        print("GraphQL falhou:", e)

    # 2) Plano B: REST (funciona com o token padrão, mas sem contribuições)
    try:
        user = _request(f"https://api.github.com/users/{login}", token)
        stats = {"repos": user["public_repos"], "seguidores": user["followers"]}
        stars, page = 0, 1
        while True:
            repos = _request(
                f"https://api.github.com/users/{login}/repos?per_page=100&page={page}&type=owner", token)
            stars += sum(r["stargazers_count"] for r in repos)
            if len(repos) < 100:
                break
            page += 1
        stats["stars"] = stars
        return stats
    except Exception as e:
        print("REST falhou:", e)
        return {}


def hello_word(x0, y0, px):
    parts, x = [], x0
    for ch in "hello":
        g = GLYPHS[ch]
        for r, row in enumerate(g):
            c = 0
            while c < len(row):
                if row[c] == "X":
                    s = c
                    while c + 1 < len(row) and row[c + 1] == "X":
                        c += 1
                    parts.append(f"M{x + s * px} {y0 + r * px}h{(c - s + 1) * px}v{px}h-{(c - s + 1) * px}z")
                c += 1
        x += (len(g[0]) + 1) * px
    return f'<path fill="{INK}" d="{"".join(parts)}"/>'


def card(x, y, w, h):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
            f'fill="{CARD}" stroke="{BORDER}"/>')


def text(x, y, s, fill=INK, weight="400", size=13, anchor="start"):
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-weight="{weight}" '
            f'font-size="{size}" text-anchor="{anchor}">{escape(str(s))}</text>')


def build():
    stats = fetch_stats()
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 500" width="900" height="500" '
         f'font-family="{MONO}" role="img" aria-label="Cartão de apresentação em estilo terminal">',
         f'<rect width="900" height="500" rx="20" fill="{BG}"/>']

    # janela fet.sh: identidade
    o.append(card(36, 36, 300, 220))
    o.append(text(56, 64, "@ fet.sh", MUTED, size=12))
    o.append(text(56, 92, CONFIG["user"], INK, "700"))
    for i, (k, v) in enumerate(CONFIG["info"]):
        o.append(text(56, 118 + i * 22, k.rjust(5), MUTED))
        o.append(text(106, 118 + i * 22, "~", MUTED))
        o.append(text(124, 118 + i * 22, v, INK))
    for i in range(6):  # barra de cores no rodapé, como no fetch original
        o.append(f'<rect x="{56 + i * 22}" y="232" width="20" height="8" '
                 f'fill="{ACCENT if i < 4 else BORDER}"/>')

    # janela gh stats: números do GitHub
    o.append(card(520, 36, 344, 196))
    o.append(text(540, 64, "$ gh stats", MUTED, size=12))
    labels = ["repos", "stars", "contribuições", "seguidores"]
    for i, k in enumerate(labels):
        yy = 100 + i * 30
        o.append(text(540, yy, k, INK))
        o.append(f'<line x1="540" x2="844" y1="{yy + 9}" y2="{yy + 9}" stroke="{BORDER}"/>')
        o.append(text(844, yy, stats.get(k, "-"), ACCENT, "700", 15, "end"))

    # palavra hello em pixels
    o.append(hello_word(345, 270, 10))

    # janela ls: projetos
    o.append(card(36, 292, 300, 118))
    o.append(text(56, 320, "~/projetos $ ls -l", MUTED, size=12))
    for i, (perm, name) in enumerate(CONFIG["projects"]):
        o.append(text(56, 352 + i * 24, perm, MUTED, size=12))
        o.append(text(160, 352 + i * 24, name, ACCENT, "700"))

    # janela status
    o.append(card(564, 292, 300, 118))
    o.append(text(584, 320, "$ status", MUTED, size=12))
    for i, (k, v) in enumerate(CONFIG["status"]):
        o.append(text(584, 346 + i * 22, k.rjust(9), MUTED))
        o.append(text(684, 346 + i * 22, "~", MUTED))
        o.append(text(702, 346 + i * 22, v, INK, "700" if k == "estágio" else "400"))

    # barra inferior
    o.append(f'<rect x="36" y="440" width="828" height="32" rx="10" fill="{CARD}" stroke="{BORDER}"/>')
    o.append(f'<circle cx="58" cy="456" r="4" fill="{ACCENT}"/>')
    o.append(text(72, 461, "luiz miguel", INK, size=12))
    for k, nav in enumerate(["sobre", "tecnologias", "projetos", "contato"]):
        o.append(text(330 + [0, 70, 170, 255][k], 461, nav, MUTED, size=12))
    o.append(text(844, 461, "recife, pe", MUTED, size=12, anchor="end"))
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "assets", "hello.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(build())
    print("ok:", os.path.normpath(out))
