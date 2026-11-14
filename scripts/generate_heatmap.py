import json
import os
import re
import urllib.request
from xml.sax.saxutils import escape

username = os.environ["GITHUB_USERNAME"]
token = os.environ["GITHUB_TOKEN"]

query = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
            color
            weekday
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

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "vinitdangi-contribution-heatmap"
    }
)

with urllib.request.urlopen(request) as response:
    result = json.loads(response.read())

if result.get("errors"):
    raise RuntimeError(json.dumps(result["errors"]))

calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
total = calendar["totalContributions"]

if not weeks or total is None:
    raise RuntimeError("GitHub returned an empty contribution calendar.")

cell = 11
gap = 4
step = cell + gap
left = 38
top = 38
width = left + len(weeks) * step + 18
height = 170

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    '<rect width="100%" height="100%" fill="#0d1117" rx="8"/>',
    '<style>text{font-family:Arial,sans-serif}.muted{fill:#8b949e}.heading{fill:#e6edf3;font-weight:600}</style>',
    f'<text x="{left}" y="17" font-size="12" class="heading">{total:,} contributions in the last year</text>',
]

for label, row in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
    y = top + row * step + 9
    parts.append(
        f'<text x="4" y="{y}" font-size="9" class="muted">{label}</text>'
    )

for col, week in enumerate(weeks):
    for day in week["contributionDays"]:
        row = int(day["weekday"])
        x = left + col * step
        y = top + row * step
        color = day["color"]

        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            color = "#161b22"

        date = escape(day["date"])
        count = int(day["contributionCount"])

        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
            f'rx="2" fill="{color}">'
            f'<title>{date}: {count} contributions</title></rect>'
        )

        if date.endswith("-01"):
            month = date[5:7]
            from calendar import month_abbr
            month_name = month_abbr[int(month)]
            parts.append(
                f'<text x="{x}" y="31" font-size="9" class="muted">{month_name}</text>'
            )

legend_y = top + 7 * step + 9
legend_x = max(left, width - 150)

parts.append(
    f'<text x="{legend_x - 34}" y="{legend_y}" font-size="9" class="muted">Less</text>'
)

for i, color in enumerate(["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]):
    parts.append(
        f'<rect x="{legend_x + i * 15}" y="{legend_y - 9}" '
        f'width="{cell}" height="{cell}" rx="2" fill="{color}"/>'
    )

parts.append(
    f'<text x="{legend_x + 85}" y="{legend_y}" font-size="9" class="muted">More</text>'
)
parts.append("</svg>")

with open("contribution-heatmap.svg", "w", encoding="utf-8") as file:
    file.write("\n".join(parts))

print(f"Generated heatmap: {total} contributions, {len(weeks)} weeks")
