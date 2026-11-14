import json
import os
import urllib.request
from datetime import date
from xml.sax.saxutils import escape

username = os.environ["GITHUB_USERNAME"]
token = os.environ["GITHUB_TOKEN"]

query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

payload = json.dumps({
    "query": query,
    "variables": {"login": username}
}).encode()

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "vinitdangi-contribution-chart"
    }
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read())

if result.get("errors"):
    raise RuntimeError(json.dumps(result["errors"]))

weeks = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

days = [
    day
    for week in weeks
    for day in week["contributionDays"]
]

days = sorted(days, key=lambda d: d["date"])[-30:]

if len(days) < 2:
    raise RuntimeError("Not enough contribution data.")

values = [int(d["contributionCount"]) for d in days]

W, H = 1100, 370
L, R, T, B = 75, 35, 45, 65
PW, PH = W - L - R, H - T - B

maximum = max(values)
ymax = max(5, ((maximum + 4) // 5) * 5)

points = []
for i, value in enumerate(values):
    x = L + i * PW / (len(values) - 1)
    y = T + PH - value / ymax * PH
    points.append((x, y))

def smooth_path(points):
    path = f"M {points[0][0]:.2f},{points[0][1]:.2f}"
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2

        c1x = p1[0] + (p2[0] - p0[0]) / 6
        c1y = p1[1] + (p2[1] - p0[1]) / 6
        c2x = p2[0] - (p3[0] - p1[0]) / 6
        c2y = p2[1] - (p3[1] - p1[1]) / 6

        path += (
            f" C {c1x:.2f},{c1y:.2f}"
            f" {c2x:.2f},{c2y:.2f}"
            f" {p2[0]:.2f},{p2[1]:.2f}"
        )
    return path

line = smooth_path(points)
baseline = T + PH
area = line + f" L {points[-1][0]:.2f},{baseline} L {points[0][0]:.2f},{baseline} Z"

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
    '<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1">',
    '<stop offset="0%" stop-color="#c084fc" stop-opacity=".55"/>',
    '<stop offset="100%" stop-color="#7c3aed" stop-opacity=".02"/>',
    '</linearGradient></defs>',
    '<rect width="100%" height="100%" rx="10" fill="#0d1117"/>',
    '<style>text{font-family:Arial,sans-serif;fill:#c9d1d9}</style>',
    '<text x="75" y="25" font-size="15" font-weight="bold">Daily Contributions — Last 30 Days</text>',
]

for tick in range(6):
    value = ymax * tick / 5
    y = T + PH - value / ymax * PH
    parts.append(f'<line x1="{L}" y1="{y:.2f}" x2="{W-R}" y2="{y:.2f}" stroke="#30363d" stroke-dasharray="3 5"/>')
    parts.append(f'<text x="{L-15}" y="{y+4:.2f}" font-size="11" text-anchor="end">{value:.0f}</text>')

for i, (day, point) in enumerate(zip(days, points)):
    if i % 3 == 0 or i == len(days) - 1:
        label = date.fromisoformat(day["date"]).strftime("%d %b")
        parts.append(
            f'<text x="{point[0]:.2f}" y="{baseline+25}" '
            f'font-size="10" text-anchor="middle">{escape(label)}</text>'
        )

parts.extend([
    f'<path d="{area}" fill="url(#area)"/>',
    f'<path d="{line}" fill="none" stroke="#c084fc" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
])

for day, (x, y) in zip(days, points):
    parts.append(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="#ffffff" stroke="#c084fc" stroke-width="2">'
        f'<title>{escape(day["date"])}: {day["contributionCount"]} contributions</title></circle>'
    )

parts.append(
    f'<text x="{W/2}" y="{H-10}" text-anchor="middle" font-size="12">Days</text>'
)
parts.append(
    f'<text transform="translate(20 {H/2}) rotate(-90)" text-anchor="middle" font-size="12">Contributions</text>'
)
parts.append('</svg>')

with open("contribution-activity.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(parts))

print(f"Generated 30-day chart. Total contributions: {sum(values)}")
