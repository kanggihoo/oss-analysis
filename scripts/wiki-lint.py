#!/usr/bin/env python3
"""Health check for /Users/kkh/Desktop/oss-analysis/wiki.

This is intentionally lightweight and dependency-free so Hermes can run it after
wiki edits. It validates the LLM Wiki operating contract, not Markdown style.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
PAGE_DIRS = ["projects", "concepts", "comparisons", "queries"]
REQUIRED_DIRS = [
    "raw",
    "raw/articles",
    "raw/papers",
    "raw/transcripts",
    "raw/assets",
    "projects",
    "concepts",
    "comparisons",
    "queries",
    "_meta",
]
REQUIRED_FILES = ["SCHEMA.md", "index.md", "log.md", "README.md"]
REQUIRED_FRONTMATTER = {"title", "created", "updated", "type", "tags", "sources", "confidence"}

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
TAG_LINE_RE = re.compile(r"^tags:\s*\[(.*?)\]\s*$", re.M)
SCHEMA_TAG_RE = re.compile(r"^- `([^`]+)`", re.M)

issues: list[str] = []
warnings: list[str] = []


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


if not WIKI.exists():
    print(f"Wiki lint: wiki directory does not exist: {WIKI}")
    sys.exit(1)

for d in REQUIRED_DIRS:
    if not (WIKI / d).is_dir():
        issues.append(f"missing required directory: wiki/{d}")

for f in REQUIRED_FILES:
    if not (WIKI / f).is_file():
        issues.append(f"missing required file: wiki/{f}")

schema_text = (WIKI / "SCHEMA.md").read_text(encoding="utf-8") if (WIKI / "SCHEMA.md").exists() else ""
index_text = (WIKI / "index.md").read_text(encoding="utf-8") if (WIKI / "index.md").exists() else ""
allowed_tags = set(SCHEMA_TAG_RE.findall(schema_text))
if not allowed_tags:
    warnings.append("could not find tag taxonomy entries in wiki/SCHEMA.md")

pages: list[Path] = []
slug_to_path: dict[str, Path] = {}
for d in PAGE_DIRS:
    base = WIKI / d
    if not base.exists():
        continue
    for page in sorted(base.rglob("*.md")):
        pages.append(page)
        if page.stem in slug_to_path:
            issues.append(f"duplicate page slug: [[{page.stem}]] at {rel(slug_to_path[page.stem])} and {rel(page)}")
        slug_to_path[page.stem] = page

for page in pages:
    text = page.read_text(encoding="utf-8")
    fm_match = FM_RE.match(text)
    if not fm_match:
        issues.append(f"missing YAML frontmatter: {rel(page)}")
        continue

    fm = fm_match.group(1)
    keys = {line.split(":", 1)[0].strip() for line in fm.splitlines() if ":" in line}
    missing = sorted(REQUIRED_FRONTMATTER - keys)
    if missing:
        issues.append(f"frontmatter missing {missing}: {rel(page)}")

    tag_match = TAG_LINE_RE.search(fm)
    if not tag_match:
        issues.append(f"frontmatter tags must be inline list: {rel(page)}")
    else:
        tags = [t.strip().strip("'\"") for t in tag_match.group(1).split(",") if t.strip()]
        if not tags:
            issues.append(f"empty tags list: {rel(page)}")
        for tag in tags:
            if allowed_tags and tag not in allowed_tags:
                issues.append(f"tag not declared in SCHEMA.md: `{tag}` in {rel(page)}")

    if f"[[{page.stem}]]" not in index_text:
        issues.append(f"page missing from index.md: [[{page.stem}]] ({rel(page)})")

    links = LINK_RE.findall(text)
    for link in links:
        if link not in slug_to_path:
            issues.append(f"broken wikilink in {rel(page)}: [[{link}]]")

    unique_links = set(links)
    if page.parent.name != "queries" and len(unique_links) < 2:
        warnings.append(f"low outbound wikilink count (<2): {rel(page)}")

    line_count = len(text.splitlines())
    if line_count > 200:
        warnings.append(f"large page over 200 lines: {rel(page)} ({line_count} lines)")

# Raw files are allowed to be plain README/policy files, but warn if raw captures
# have no provenance block. Skip README.md because it documents the directory.
raw_dir = WIKI / "raw"
if raw_dir.exists():
    for raw_page in sorted(raw_dir.rglob("*.md")):
        if raw_page.name == "README.md":
            continue
        text = raw_page.read_text(encoding="utf-8")
        if not FM_RE.match(text):
            warnings.append(f"raw capture missing frontmatter/provenance: {rel(raw_page)}")

print(f"Wiki lint: {len(issues)} issue(s), {len(warnings)} warning(s), {len(pages)} indexed page(s)")

if issues:
    print("\nIssues:")
    for item in issues:
        print(f"- {item}")

if warnings:
    print("\nWarnings:")
    for item in warnings:
        print(f"- {item}")

sys.exit(1 if issues else 0)
