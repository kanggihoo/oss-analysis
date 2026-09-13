#!/usr/bin/env python3
"""Temporary Codex Python SDK test for translation loop + context-window usage.

Run with:
  uv run --no-project --isolated --prerelease allow --with openai-codex python run_translation_context_test.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from openai_codex import ApprovalMode, Codex, CodexConfig, Sandbox
from openai_codex.types import ReasoningEffort

MODEL = "gpt-5.4-mini"
EFFORT = ReasoningEffort.medium
WORKSPACE = Path(__file__).resolve().parent
INPUT_DIR = WORKSPACE / "inputs"
OUTPUT_DIR = WORKSPACE / "outputs"
REPORT_PATH = WORKSPACE / "translation_context_report.json"
# Real workflows would set this high, e.g. 0.70 or 0.80. For this smoke test we
# only demonstrate the calculation; the tiny samples probably won't cross it.
NEW_THREAD_AT_CONTEXT_RATIO = 0.80


def usage_to_dict(usage: Any) -> dict[str, Any] | None:
    if usage is None:
        return None

    def breakdown_to_dict(b: Any) -> dict[str, int]:
        return {
            "input_tokens": int(getattr(b, "input_tokens", 0)),
            "cached_input_tokens": int(getattr(b, "cached_input_tokens", 0)),
            "output_tokens": int(getattr(b, "output_tokens", 0)),
            "reasoning_output_tokens": int(getattr(b, "reasoning_output_tokens", 0)),
            "total_tokens": int(getattr(b, "total_tokens", 0)),
        }

    total = breakdown_to_dict(usage.total)
    window = getattr(usage, "model_context_window", None)
    ratio = None
    if window:
        ratio = total["total_tokens"] / int(window)
    return {
        "model_context_window": window,
        "last": breakdown_to_dict(usage.last),
        "total": total,
        "context_ratio": ratio,
    }


def should_rotate_thread(usage_dict: dict[str, Any] | None) -> bool:
    if not usage_dict or usage_dict.get("context_ratio") is None:
        return False
    return usage_dict["context_ratio"] >= NEW_THREAD_AT_CONTEXT_RATIO


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Programmatic control of the local Codex runtime environment.
    # Keep the current env so existing ~/.codex auth/session and PATH continue to work,
    # but add a marker and explicit cwd for this test.
    env = dict(os.environ)
    env["CODEX_SDK_TRANSLATION_TEST"] = "1"
    # Hermes tool shell HOME is profile-scoped, so point Codex at the user's
    # existing local Codex auth/config directory for this subscription-auth test.
    env["HOME"] = "/Users/kkh"
    env["CODEX_HOME"] = "/Users/kkh/.codex"

    config = CodexConfig(
        cwd=str(WORKSPACE),
        env=env,
        client_name="oss_analyst_codex_sdk_context_test",
        client_title="oss-analyst Codex SDK context test",
        config_overrides=(
            # Demonstrate config override plumbing. Network is unnecessary for local translation.
            "sandbox_workspace_write.network_access=false",
        ),
    )

    records: list[dict[str, Any]] = []

    with Codex(config) as codex:
        # Confirm the desired model is visible if the runtime exposes a model list.
        visible_models: list[str] = []
        try:
            models_response = codex.models(include_hidden=True)
            raw_models = getattr(models_response, "data", None) or getattr(models_response, "models", None) or getattr(models_response, "items", None) or []
            for m in raw_models:
                mid = getattr(m, "id", None) or getattr(m, "name", None) or str(m)
                visible_models.append(str(mid))
        except Exception as exc:  # model listing is not required for the turn test
            visible_models.append(f"models() failed: {type(exc).__name__}: {exc}")

        thread = codex.thread_start(
            cwd=str(WORKSPACE),
            model=MODEL,
            sandbox=Sandbox.workspace_write,
            approval_mode=ApprovalMode.auto_review,
        )
        current_thread_id = thread.id

        for index, input_path in enumerate(sorted(INPUT_DIR.glob("*.txt")), start=1):
            source_text = input_path.read_text(encoding="utf-8")
            prompt = (
                "Translate the following English text into natural Korean.\n"
                "Return only the Korean translation, with no commentary.\n\n"
                f"SOURCE_FILE: {input_path.name}\n"
                "TEXT:\n"
                f"{source_text}"
            )
            result = thread.run(prompt, model=MODEL, effort=EFFORT, sandbox=Sandbox.read_only)
            usage_dict = usage_to_dict(result.usage)
            translation = result.final_response or ""
            out_path = OUTPUT_DIR / f"{input_path.stem}.ko.txt"
            out_path.write_text(translation, encoding="utf-8")

            record = {
                "index": index,
                "input_file": str(input_path.relative_to(WORKSPACE)),
                "output_file": str(out_path.relative_to(WORKSPACE)),
                "thread_id": current_thread_id,
                "turn_id": result.id,
                "status": str(result.status),
                "usage": usage_dict,
                "translation_preview": translation[:240],
            }
            records.append(record)

            if should_rotate_thread(usage_dict):
                thread = codex.thread_start(
                    cwd=str(WORKSPACE),
                    model=MODEL,
                    sandbox=Sandbox.workspace_write,
                    approval_mode=ApprovalMode.auto_review,
                )
                current_thread_id = thread.id
                records.append({
                    "event": "rotated_thread",
                    "reason": f"context_ratio >= {NEW_THREAD_AT_CONTEXT_RATIO}",
                    "new_thread_id": current_thread_id,
                })

    report = {
        "model_requested": MODEL,
        "effort_requested": str(EFFORT),
        "workspace": str(WORKSPACE),
        "new_thread_at_context_ratio": NEW_THREAD_AT_CONTEXT_RATIO,
        "visible_model_sample": visible_models[:20],
        "model_visible_exact_match": MODEL in visible_models,
        "records": records,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
