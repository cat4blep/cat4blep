#!/usr/bin/env python3
"""Refresh the local Modrinth and CurseForge download counter SVGs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
USER_AGENT = "cat4blep-profile-counters/1.0 (+https://github.com/cat4blep/cat4blep)"

# CurseForge's public API requires a key. CFWidget exposes the same public project
# totals without credentials, so the workflow can refresh these profile badges.
CURSEFORGE_PROJECT_IDS = {
    1512427: "SeeU",
    1513601: "Weight of Steel",
    1516292: "Armor Chroma Refabricated",
    1545329: "EMI Recipe Pin",
    1522605: "ChTR",
    1514207: "B&W Shader",
}


def get_json(url: str) -> object:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def compact(value: int) -> str:
    for divisor, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if value >= divisor:
            short = f"{value / divisor:.1f}".rstrip("0").rstrip(".")
            return f"{short}{suffix}"
    return f"{value:,}"


def badge(platform: str, total: int, color: str, tint: str, panel_width: int) -> str:
    visible = compact(total)
    display_name = {"modrinth": "Modrinth", "curseforge": "CurseForge"}[platform]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="44" viewBox="0 0 300 44" role="img" aria-labelledby="title desc">
  <title id="title">{display_name} total downloads: {total:,}</title>
  <desc id="desc">Automatically updated daily.</desc>
  <rect x="0.5" y="0.5" width="299" height="43" fill="#0b1020" stroke="{color}" stroke-opacity="{0.55 if platform == 'modrinth' else 0.60:.2f}"/>
  <rect x="1" y="1" width="{panel_width}" height="42" fill="{color}" fill-opacity="{0.12 if platform == 'modrinth' else 0.13:.2f}"/>
  <path d="M20 12v13m0 0-5-5m5 5 5-5M14 31h12" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="35" y="27" fill="{tint}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="12" font-weight="700">{platform.upper()}</text>
  <text x="284" y="27" text-anchor="end" fill="#f8fafc" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="13" font-weight="700">{visible} downloads</text>
</svg>
'''


def totals() -> tuple[int, int]:
    modrinth_projects = get_json("https://api.modrinth.com/v2/user/Cat4blep/projects")
    if not isinstance(modrinth_projects, list):
        raise RuntimeError("Unexpected Modrinth response")
    modrinth_total = sum(int(project["downloads"]) for project in modrinth_projects)

    curseforge_total = 0
    for project_id, project_name in CURSEFORGE_PROJECT_IDS.items():
        project = get_json(f"https://api.cfwidget.com/{project_id}")
        if not isinstance(project, dict):
            raise RuntimeError(f"Unexpected CurseForge response for {project_name}")
        owners = {str(member.get("username", "")).casefold() for member in project.get("members", [])}
        if "cat4blep" not in owners:
            raise RuntimeError(f"Ownership check failed for {project_name}")
        curseforge_total += int(project["downloads"]["total"])

    return modrinth_total, curseforge_total


def main() -> int:
    modrinth_total, curseforge_total = totals()
    generated = {
        ASSETS / "modrinth-downloads.svg": badge(
            "modrinth", modrinth_total, "#1bd96a", "#bbf7d0", 124
        ),
        ASSETS / "curseforge-downloads.svg": badge(
            "curseforge", curseforge_total, "#f16436", "#fed7aa", 132
        ),
    }

    if "--check" in sys.argv:
        stale = [str(path.relative_to(ROOT)) for path, content in generated.items() if path.read_text(encoding="utf-8") != content]
        if stale:
            print("Stale counters: " + ", ".join(stale))
            return 1
        print(f"Counters are current: Modrinth={modrinth_total:,}, CurseForge={curseforge_total:,}")
        return 0

    for path, content in generated.items():
        path.write_text(content, encoding="utf-8", newline="\n")
    print(f"Updated counters: Modrinth={modrinth_total:,}, CurseForge={curseforge_total:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
