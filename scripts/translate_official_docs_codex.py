#!/usr/bin/env python3
"""Translate captured official Markdown docs to Korean with Codex SDK.

Input defaults:
  artifacts/<repo>/official/**/*.md

Output defaults:
  official-ko/<repo>/**/*.md

Run log defaults:
  artifacts/<repo>/official/translation-runs/<timestamp>-codex-ko.jsonl
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKSPACE_DEFAULT = Path("/Users/kkh/Desktop/oss-analysis")
BASE_SCRIPT = Path("/Users/kkh/.hermes/profiles/oss-analyst/skills/research/deepwiki-codex-translation/scripts/translate_deepwiki_codex.py")
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_EFFORT = "medium"
DEFAULT_ROTATE_AT = 0.70
DEFAULT_MAX_RETRIES = 1
SCRIPT_VERSION = "official-1.0.0"

spec = importlib.util.spec_from_file_location("deepwiki_translate_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load base translation script: {BASE_SCRIPT}")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


@dataclass
class OfficialTask:
    repo: str
    order: int
    source_abs: Path
    target_abs: Path
    source_rel: str
    target_rel: str
    rel_md: str
    title: str
    frontmatter: str

    @property
    def slug(self) -> str:
        return self.rel_md[:-3] if self.rel_md.endswith(".md") else self.rel_md

    @property
    def section(self) -> str:
        return str(self.order)

    @property
    def url(self) -> str:
        return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate artifacts/<repo>/official/**/*.md into official-ko/<repo> using Codex SDK.")
    parser.add_argument("repo", help="Repo artifact name, e.g. agent-browser")
    parser.add_argument("--workspace", type=Path, default=WORKSPACE_DEFAULT, help=f"Workspace root (default: {WORKSPACE_DEFAULT})")
    parser.add_argument("--source-dir", type=Path, default=None, help="Source directory, default artifacts/<repo>/official")
    parser.add_argument("--target-dir", type=Path, default=None, help="Target directory, default official-ko/<repo>")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Codex model (default: {DEFAULT_MODEL})")
    parser.add_argument("--effort", default=DEFAULT_EFFORT, choices=["none", "minimal", "low", "medium", "high", "xhigh"], help=f"Reasoning effort (default: {DEFAULT_EFFORT})")
    parser.add_argument("--rotate-at", type=float, default=DEFAULT_ROTATE_AT, help=f"Rotate thread when previous active context ratio >= threshold (default: {DEFAULT_ROTATE_AT})")
    parser.add_argument("--force", action="store_true", help="Re-translate even if target file already exists")
    parser.add_argument("--limit", type=int, default=None, help="Translate at most N files")
    parser.add_argument("--dry-run", action="store_true", help="Build paths/index/log plan without invoking Codex")
    parser.add_argument("--auth-home", type=Path, default=None, help="Home directory containing .codex auth, e.g. /Users/kkh")
    parser.add_argument("--log-path", type=Path, default=None, help="Optional JSONL log path override under workspace")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES, help=f"Retry a file after validation failure or missing temp output (default: {DEFAULT_MAX_RETRIES})")
    return parser.parse_args()


def title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1).strip().replace("|", "¦")
    return fallback.replace("|", "¦")


def frontmatter_for(repo: str, source_rel: str, order: int, title: str) -> str:
    safe_title = str(title).replace('"', '\\"').replace("\n", " ")
    return (
        "---\n"
        "type: official-doc-translation\n"
        f"repo: {repo}\n"
        f"source: {source_rel}\n"
        f"order: {order}\n"
        f"title: \"{safe_title}\"\n"
        "---"
    )


def build_tasks(workspace: Path, repo: str, source_dir: Path, target_dir: Path) -> list[OfficialTask]:
    base.validate_repo_name(repo)
    base.ensure_under(source_dir, workspace, "source directory")
    base.ensure_under(target_dir, workspace / "official-ko", "target directory")
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Missing source directory: {source_dir}")
    source_files = sorted(p for p in source_dir.rglob("*.md") if p.is_file())
    tasks: list[OfficialTask] = []
    for idx, source_abs in enumerate(source_files, start=1):
        rel = source_abs.relative_to(source_dir).as_posix()
        if rel.startswith(".") or ".." in Path(rel).parts:
            raise ValueError(f"Unsafe relative path: {rel}")
        target_abs = target_dir / rel
        base.ensure_under(source_abs, source_dir, "source file")
        base.ensure_under(target_abs, target_dir, "target file")
        source_text = source_abs.read_text(encoding="utf-8")
        title = title_from_markdown(source_text, Path(rel).stem)
        source_rel = base.rel_posix(source_abs, workspace)
        target_rel = base.rel_posix(target_abs, workspace)
        frontmatter = frontmatter_for(repo, source_rel, idx, title)
        tasks.append(OfficialTask(repo, idx, source_abs, target_abs, source_rel, target_rel, rel, title, frontmatter))
    return tasks


def build_index(repo: str, source_dir_rel: str, tasks: list[OfficialTask]) -> str:
    lines = [
        "---",
        "type: official-doc-translation-index",
        f"repo: {repo}",
        f"source_dir: {source_dir_rel}",
        "---",
        "",
        f"# Official Docs Translation: {repo}",
        "",
        "> 이 문서는 공식 문서 Markdown 산출물의 한국어 번역입니다. 코드 검증이 완료된 최종 분석 보고서가 아닙니다.",
        "",
        "## TOC",
        "",
    ]
    for task in tasks:
        link = task.rel_md[:-3] if task.rel_md.endswith(".md") else task.rel_md
        alias = f"{task.order:02d} {task.title}".replace("|", "¦")
        lines.append(f"- [[{link}|{alias}]]")
    lines.append("")
    return "\n".join(lines)


LINK_TARGET_RE = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)")


def markdown_link_targets(text: str) -> set[str]:
    return {m.group(1).strip() for m in LINK_TARGET_RE.finditer(base.FENCE_RE.sub("", text))}


def validate_official_translation(source_text: str, target_text: str, frontmatter: str) -> Any:
    result = base.validate_translation(source_text, target_text, frontmatter)
    errors = list(result.errors)
    warnings = list(result.warnings)
    source_links = markdown_link_targets(base.strip_frontmatter(source_text))
    target_links = markdown_link_targets(base.strip_frontmatter(target_text))
    missing_links = sorted(source_links - target_links)
    if missing_links:
        errors.append(f"markdown_link_targets_missing:{missing_links[:10]}")
    metrics = dict(result.metrics)
    metrics["source_link_targets"] = len(source_links)
    metrics["target_link_targets"] = len(target_links)
    return base.ValidationResult(valid=not errors, errors=errors, warnings=warnings, metrics=metrics)


def translation_prompt(task: OfficialTask, output_abs: Path, output_rel: str, attempt: int, previous_errors: list[str] | None = None) -> str:
    previous_error_text = ""
    if previous_errors:
        previous_error_text = "\nPrevious attempt failed validation with these errors. Correct them in this attempt:\n" + "\n".join(f"- {e}" for e in previous_errors) + "\n"
    return f"""Translate this official agent-browser Markdown document into Korean and write it to the temporary output file.

Repository: {task.repo}
Source file absolute path:
{task.source_abs}

Temporary output file absolute path (WRITE HERE ONLY):
{output_abs}

Temporary output Obsidian-relative path:
{output_rel}

Final target file absolute path (DO NOT WRITE DIRECTLY; the Python script will atomically move the temporary file after validation):
{task.target_abs}

Final target Obsidian-relative path:
{task.target_rel}

Document title: {task.title}
Order: {task.order}
Attempt: {attempt}
{previous_error_text}
Rules:
- Read the source Markdown file from the source path.
- Translate prose, headings, list text, and explanatory table cells into natural Korean.
- Preserve Markdown structure.
- Preserve fenced code blocks exactly, including Mermaid blocks and shell command examples.
- Preserve file paths, URLs, Markdown link destinations, source references, inline code, function names, class names, package names, command names, flags, and identifiers.
- Do not translate filenames.
- Write the final translated Markdown to the temporary output file only.
- The output file must start with this exact YAML frontmatter:

{task.frontmatter}

Do not write commentary anywhere. Only create or update the temporary Markdown file.
"""


def resolve_log_path(workspace: Path, default_log_path: Path, override: Path | None) -> Path:
    if override is None:
        log_path = default_log_path
    else:
        log_path = override.expanduser()
        if not log_path.is_absolute():
            log_path = workspace / log_path
    log_path = log_path.resolve()
    base.ensure_under(log_path, workspace, "log path")
    return log_path


def main() -> int:
    args = parse_args()
    workspace = args.workspace.expanduser().resolve()
    repo = args.repo
    source_dir = (args.source_dir.expanduser() if args.source_dir else workspace / "artifacts" / repo / "official")
    if not source_dir.is_absolute():
        source_dir = workspace / source_dir
    source_dir = source_dir.resolve()
    target_dir = (args.target_dir.expanduser() if args.target_dir else workspace / "official-ko" / repo)
    if not target_dir.is_absolute():
        target_dir = workspace / target_dir
    target_dir = target_dir.resolve()
    log_dir = source_dir / "translation-runs"
    log_path = resolve_log_path(workspace, log_dir / f"{base.timestamp_for_path()}-codex-ko.jsonl", args.log_path)
    completed = 0
    skipped = 0
    failed = 0
    rotations = 0
    thread_ids: list[str] = []
    run_started = time.monotonic()

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir = target_dir / ".translation-tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tasks = build_tasks(workspace, repo, source_dir, target_dir)
        if args.limit is not None:
            tasks = tasks[: args.limit]

        base.write_log(log_path, "run_start", repo=repo, workspace=str(workspace), source_dir=base.rel_posix(source_dir, workspace), target_dir=base.rel_posix(target_dir, workspace), model=args.model, effort=args.effort, rotate_at=args.rotate_at, max_retries=args.max_retries, dry_run=args.dry_run, script_version=SCRIPT_VERSION, argv=sys.argv)
        index_path = target_dir / "00-index.md"
        index_path.write_text(build_index(repo, base.rel_posix(source_dir, workspace), tasks), encoding="utf-8")
        base.write_log(log_path, "index_written", path=base.rel_posix(index_path, workspace), links=len(tasks))
        for task in tasks:
            base.write_log(log_path, "file_mapped", order=task.order, slug=task.slug, title=task.title, source=task.source_rel, target=task.target_rel, source_exists=task.source_abs.exists(), source_bytes=task.source_abs.stat().st_size if task.source_abs.exists() else None)

        if args.dry_run:
            elapsed = round(time.monotonic() - run_started, 3)
            summary = {"repo": repo, "completed": 0, "skipped": 0, "failed": 0, "dry_run": True, "tasks": len(tasks), "target_dir": base.rel_posix(target_dir, workspace), "index": base.rel_posix(index_path, workspace), "log_path": base.rel_posix(log_path, workspace), "elapsed_seconds": elapsed, "script_version": SCRIPT_VERSION}
            base.write_log(log_path, "run_done", **summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

        from openai_codex import Codex, CodexConfig, Sandbox

        auth_home = base.detect_auth_home(workspace, args.auth_home)
        env = base.build_codex_env(workspace, auth_home)
        config = CodexConfig(cwd=str(workspace), env=env, client_name="oss_analyst_official_docs_translation", client_title="oss-analyst official docs Korean translation")
        effort = base.get_reasoning_effort(args.effort)
        last_usage: Any = None
        last_total_usage: dict[str, Any] | None = None

        with Codex(config) as codex:
            thread = base.start_thread(codex, workspace, args.model)
            thread_ids.append(thread.id)
            base.write_log(log_path, "thread_start", thread_id=thread.id, model=args.model, reason="initial", auth_home=str(auth_home) if auth_home else None)

            for task in tasks:
                if not task.source_abs.exists():
                    failed += 1
                    base.write_log(log_path, "translate_failed", order=task.order, slug=task.slug, reason="missing_source", source=task.source_rel)
                    continue
                if task.target_abs.exists() and not args.force:
                    skipped += 1
                    base.write_log(log_path, "translate_skipped", order=task.order, slug=task.slug, reason="target_exists", target=task.target_rel)
                    continue

                previous_ratio = base.active_ratio_from_usage(last_usage)
                if previous_ratio is not None and previous_ratio >= args.rotate_at:
                    old_thread_id = thread.id
                    thread = base.start_thread(codex, workspace, args.model)
                    rotations += 1
                    thread_ids.append(thread.id)
                    base.write_log(log_path, "thread_rotate", old_thread_id=old_thread_id, new_thread_id=thread.id, reason="active_context_ratio", previous_active_context_ratio=previous_ratio, rotate_at=args.rotate_at)

                task.target_abs.parent.mkdir(parents=True, exist_ok=True)
                source_text = task.source_abs.read_text(encoding="utf-8")
                source_sha = base.sha256_text(source_text)
                previous_target_text = task.target_abs.read_text(encoding="utf-8") if task.target_abs.exists() else None
                previous_target_sha = base.sha256_text(previous_target_text) if previous_target_text is not None else None
                base.write_log(log_path, "source_read", order=task.order, slug=task.slug, source=task.source_rel, bytes=len(source_text.encode("utf-8")), sha256=source_sha)

                attempt_errors: list[str] | None = None
                success = False
                file_started = time.monotonic()
                usage_dict = None
                tmp_abs = tmp_dir / f"{task.slug.replace('/', '__')}.{os.getpid()}.{task.order}.md"
                base.ensure_under(tmp_abs, tmp_dir, "temporary output file")
                tmp_rel = base.rel_posix(tmp_abs, workspace)

                for attempt in range(1, max(1, args.max_retries + 1) + 1):
                    if tmp_abs.exists():
                        tmp_abs.unlink()
                    base.write_log(log_path, "translate_start", order=task.order, slug=task.slug, attempt=attempt, thread_id=thread.id, source=task.source_rel, target=task.target_rel, temporary_target=tmp_rel)
                    try:
                        result = thread.run(translation_prompt(task, tmp_abs, tmp_rel, attempt, attempt_errors), model=args.model, effort=effort, sandbox=Sandbox.workspace_write)
                        last_usage = result.usage
                        usage_dict = base.usage_to_dict(result.usage)
                        last_total_usage = usage_dict
                        if not tmp_abs.exists():
                            attempt_errors = ["temporary_output_not_created"]
                            base.write_log(log_path, "translate_attempt_failed", order=task.order, slug=task.slug, attempt=attempt, thread_id=thread.id, turn_id=getattr(result, "id", None), status=str(getattr(result, "status", "unknown")), reason="temporary_output_not_created", usage=usage_dict)
                            continue

                        frontmatter_action = base.normalize_frontmatter(tmp_abs, task.frontmatter)
                        tmp_text = tmp_abs.read_text(encoding="utf-8")
                        validation = validate_official_translation(source_text, tmp_text, task.frontmatter)
                        if not validation.valid:
                            attempt_errors = validation.errors
                            base.write_log(log_path, "translate_attempt_failed", order=task.order, slug=task.slug, attempt=attempt, thread_id=thread.id, turn_id=getattr(result, "id", None), status=str(getattr(result, "status", "unknown")), reason="validation_failed", validation_errors=validation.errors, validation_warnings=validation.warnings, validation_metrics=validation.metrics, frontmatter_action=frontmatter_action, usage=usage_dict)
                            continue

                        os.replace(tmp_abs, task.target_abs)
                        target_text = task.target_abs.read_text(encoding="utf-8")
                        target_sha = base.sha256_text(target_text)
                        completed += 1
                        success = True
                        elapsed = round(time.monotonic() - file_started, 3)
                        base.write_log(log_path, "translate_done", order=task.order, slug=task.slug, attempt=attempt, thread_id=thread.id, turn_id=getattr(result, "id", None), status=str(getattr(result, "status", "unknown")), source=task.source_rel, source_sha256=source_sha, target=task.target_rel, target_bytes=len(target_text.encode("utf-8")), target_sha256=target_sha, previous_target_sha256=previous_target_sha, target_changed=(previous_target_sha != target_sha), atomic_replace=True, frontmatter_action=frontmatter_action, validation_warnings=validation.warnings, validation_metrics=validation.metrics, elapsed_seconds=elapsed, usage=usage_dict)
                        break
                    except Exception as exc:
                        attempt_errors = [f"{type(exc).__name__}: {exc}"]
                        base.write_log(log_path, "translate_attempt_failed", order=task.order, slug=task.slug, attempt=attempt, thread_id=thread.id, reason=type(exc).__name__, message=str(exc))

                if not success:
                    failed += 1
                    if tmp_abs.exists():
                        tmp_abs.unlink()
                    base.write_log(log_path, "translate_failed", order=task.order, slug=task.slug, thread_id=thread.id, reason="exhausted_retries", validation_errors=attempt_errors or [], attempts=max(1, args.max_retries + 1), usage=usage_dict)

        elapsed = round(time.monotonic() - run_started, 3)
        summary = {"repo": repo, "completed": completed, "skipped": skipped, "failed": failed, "target_dir": base.rel_posix(target_dir, workspace), "index": base.rel_posix(index_path, workspace), "log_path": base.rel_posix(log_path, workspace), "elapsed_seconds": elapsed, "thread_count": len(set(thread_ids)), "thread_rotations": rotations, "thread_ids": thread_ids, "last_usage": last_total_usage, "script_version": SCRIPT_VERSION}
        base.write_log(log_path, "run_done", **summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if failed == 0 else 1
    except Exception as exc:
        try:
            base.write_log(log_path, "run_aborted", repo=repo, completed=completed, skipped=skipped, failed=failed, thread_count=len(set(thread_ids)), thread_rotations=rotations, exception=type(exc).__name__, message=str(exc), elapsed_seconds=round(time.monotonic() - run_started, 3), script_version=SCRIPT_VERSION)
        except Exception as log_exc:
            print(f"ERROR: failed to write run_aborted log: {type(log_exc).__name__}: {log_exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
