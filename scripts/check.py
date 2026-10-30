#!/usr/bin/env python3
"""reports 문서의 기계적 완료 조건을 점검한다 (OSS_ANALYSIS_WORKFLOW.md 1·4·6장).

사용: python scripts/check.py [repo ...]     # 인자가 없으면 전체

점검 항목
  sha     overview frontmatter sha == repo-metadata.txt(commit= / head_sha:) 또는 <주제>/repos.lock.tsv
  index   index.md에 레포 행이 있고, 그 행의 SHA가 overview sha와 같다
  status  스펙 frontmatter status == overview feature map의 상태 == index.md의 상태(적혀 있을 때)
  link    reports 문서의 상대 링크가 가리키는 파일이 있다

ERROR는 값이 서로 다르거나 링크가 깨진 것, NOTE는 값이 비어 비교하지 못한 것(이전 문서는 소급하지 않는다, SCHEMA.md).
ERROR가 하나라도 있으면 종료 코드 1.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS_WORDS = ("ready", "draft", "미작성")


def workspaces():
    """(주제 폴더 이름 또는 '', 경로). 루트와 GUIDE.md·reports/가 있는 주제 폴더."""
    yield "", ROOT
    for d in sorted(ROOT.iterdir()):
        if d.is_dir() and (d / "GUIDE.md").is_file() and (d / "reports").is_dir():
            yield d.name, d


def frontmatter(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            k, sep, v = line.partition(":")
            if sep and not line.startswith((" ", "-")):
                fm[k.strip()] = v.split("#")[0].strip().strip('"').strip("'")
    return fm, text


def metadata_sha(ws, repo):
    meta = ws / "artifacts" / repo / "repo-metadata.txt"
    if meta.is_file():
        m = re.search(r"^(?:commit=|head_sha:\s*)([0-9a-f]{7,40})", meta.read_text(encoding="utf-8", errors="replace"), re.M)
        if m:
            return m.group(1), "repo-metadata.txt"
    lock = ws / "repos.lock.tsv"
    if lock.is_file():
        for line in lock.read_text(encoding="utf-8").splitlines():
            cols = line.split("\t")
            if len(cols) >= 4 and cols[0] == repo:
                return cols[3], "repos.lock.tsv"
    return "", ""


def index_rows():
    rows = {}
    for line in (ROOT / "index.md").read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        m = re.match(r"^(\S+)(?:\s+\(([^)]+)/\))?$", cells[0])
        if m:
            rows[(m.group(2) or "", m.group(1))] = cells
    return rows


def index_statuses(cells):
    """index 행의 스펙 칸에서 {slug: status}. '(모두 ready)'처럼 묶어 쓴 상태는 개별 표기가 없는 링크에 적용."""
    text = cells[-1] if cells else ""
    group = re.search(r"모두\s*(ready|draft)", text)
    out = {}
    for m in re.finditer(r"\[[^\]]*\]\([^)]*capabilities/([\w.-]+)\.md\)\s*\(?\s*(ready|draft)?", text):
        st = m.group(2) or (group.group(1) if group else None)
        if st:
            out[m.group(1)] = st
    return out


def map_statuses(overview_text):
    """overview feature map에서 {slug: status}. 'capabilities/<slug>.md ... · <상태>' 형태."""
    out = {}
    pat = r"capabilities/([\w.-]+)\.md[)`]*\s*[·(]\s*(" + "|".join(STATUS_WORDS) + ")"
    for m in re.finditer(pat, overview_text):
        out.setdefault(m.group(1), m.group(2))
    return out


def broken_links(md):
    text = md.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"```.*?```|`[^`\n]*`", "", text, flags=re.S)  # 코드 블록·인라인 코드 안의 예시 링크 제외
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"^[a-z]+:", target) or target.startswith(("#", "/")) or "<" in target:
            continue
        path = target.split("#")[0]
        if path and not (md.parent / path).exists():
            yield target


def main(only):
    errors, notes = [], []
    rows = index_rows()
    for topic, ws in workspaces():
        for ov in sorted((ws / "reports").glob("*/overview.md")):
            repo = ov.parent.name
            if only and repo not in only:
                continue
            name = f"{topic}/{repo}" if topic else repo
            fm, text = frontmatter(ov)
            sha = fm.get("sha", "")

            meta, src = metadata_sha(ws, repo)
            if not sha or not meta:
                notes.append(f"[sha] {name}: 비교 불가 (overview sha={sha[:7] or '없음'}, 메타={meta[:7] or '없음'})")
            elif not meta.startswith(sha) and not sha.startswith(meta):
                errors.append(f"[sha] {name}: overview {sha[:7]} != {src} {meta[:7]}")

            cells = rows.get((topic, repo))
            if cells is None:
                errors.append(f"[index] {name}: index.md에 행 없음")
            elif sha and sha[:7] not in cells[1]:
                errors.append(f"[index] {name}: index SHA {cells[1]} != overview {sha[:7]}")

            mapped = map_statuses(text)
            indexed = index_statuses(cells) if cells else {}
            for spec in sorted((ov.parent / "capabilities").glob("*.md")):
                slug = spec.stem
                st = frontmatter(spec)[0].get("status", "")
                if not st:
                    notes.append(f"[status] {name}/{slug}: frontmatter status 없음")
                    continue
                if mapped.get(slug) not in (None, st):
                    errors.append(f"[status] {name}/{slug}: 스펙 {st} != feature map {mapped[slug]}")
                if slug not in mapped:
                    notes.append(f"[status] {name}/{slug}: feature map에서 상태를 찾지 못함")
                if indexed.get(slug) not in (None, st):
                    errors.append(f"[status] {name}/{slug}: 스펙 {st} != index {indexed[slug]}")
            for slug, st in mapped.items():
                if st != "미작성" and not (ov.parent / "capabilities" / f"{slug}.md").is_file():
                    errors.append(f"[status] {name}/{slug}: feature map에 {st}인데 파일 없음")

            for md in sorted(ov.parent.rglob("*.md")):
                for target in broken_links(md):
                    errors.append(f"[link] {md.relative_to(ROOT).as_posix()}: {target}")

    for line in notes:
        print("NOTE  " + line)
    for line in errors:
        print("ERROR " + line)
    print(f"\nERROR {len(errors)} / NOTE {len(notes)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(set(sys.argv[1:])))
