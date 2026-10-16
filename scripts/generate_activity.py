#!/usr/bin/env python3
"""Build assets/activity.svg (12-month contribution bars) from GitHub's own data.
Standard library only. Set MOCK=1 to test the rendering without a token."""
import json, os, random, urllib.request
from datetime import date, datetime, timezone

USER = os.environ.get("GH_USER", "Shahriar-Hossain-Alvi")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT", "assets/activity.svg")

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""

def month_keys(today, n=12):
    y, m, keys = today.year, today.month, []
    for _ in range(n):
        keys.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return keys[::-1]

def fetch_days(today, start):
    if os.environ.get("MOCK"):
        random.seed(7)
        return {f"{y}-{m:02d}": random.randint(5, 120) for y, m in month_keys(today)}
    body = json.dumps({"query": QUERY, "variables": {
        "login": USER,
        "from": f"{start.isoformat()}T00:00:00Z",
        "to": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
        "User-Agent": "profile-activity-graph"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("errors") or not data.get("data", {}).get("user"):
        raise SystemExit(f"GitHub API error: {data}")
    totals = {}
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    for w in cal["weeks"]:
        for d in w["contributionDays"]:
            totals[d["date"][:7]] = totals.get(d["date"][:7], 0) + d["contributionCount"]
    return totals

def render(keys, totals, today):
    W, H, left, right, top, base = 840, 250, 40, 40, 70, 190
    vals = [totals.get(f"{y}-{m:02d}", 0) for y, m in keys]
    peak = max(max(vals), 1)
    slot = (W - left - right) / len(keys)
    bw = slot * 0.58
    names = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="GitHub contributions per month for the last 12 months, {sum(vals)} in total">',
           f'<rect width="{W}" height="{H}" rx="14" fill="#0F1F2E"/>',
           f'<text x="{left}" y="38" font-family="Georgia, serif" font-size="22" font-weight="700" fill="#F4F7FA">Contributions in the last 12 months</text>',
           f'<text x="{W-right}" y="38" text-anchor="end" font-family="monospace" font-size="16" fill="#7DD3C0">{sum(vals)} total</text>',
           f'<line x1="{left}" y1="{base}" x2="{W-right}" y2="{base}" stroke="#8FA3B5" stroke-opacity="0.4"/>']
    for i, ((y, m), v) in enumerate(zip(keys, vals)):
        h = (base - top - 18) * v / peak
        x = left + i * slot + (slot - bw) / 2
        out.append(f'<rect x="{x:.1f}" y="{base-h:.1f}" width="{bw:.1f}" height="{max(h,2):.1f}" rx="3" fill="#7DD3C0" fill-opacity="{0.35 + 0.65*v/peak:.2f}"/>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{base-h-6:.1f}" text-anchor="middle" font-family="monospace" font-size="12" fill="#F4F7FA">{v}</text>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{base+20}" text-anchor="middle" font-family="monospace" font-size="12" fill="#8FA3B5">{names[m-1]}</text>')
    out.append(f'<text x="{W-right}" y="{H-14}" text-anchor="end" font-family="monospace" font-size="11" fill="#8FA3B5">updated {today.isoformat()}</text>')
    out.append("</svg>")
    return "\n".join(out)

if __name__ == "__main__":
    today = datetime.now(timezone.utc).date()
    keys = month_keys(today)
    start = date(keys[0][0], keys[0][1], 1)
    svg = render(keys, fetch_days(today, start), today)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(svg)
    print("wrote", OUT)
