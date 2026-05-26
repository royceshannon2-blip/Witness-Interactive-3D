#!/usr/bin/env python3
"""
generate_ref_image.py — Stage 0 of the Witness Asset Pipeline

Generates the reference image (`ref.png`) that Hunyuan3D 2.1 consumes in
stage 1, by driving a local ComfyUI server with a Flux.1 [dev] workflow.

Flow:
  1. Read the asset's `<id>.md` template — frontmatter + body.
  2. Build a Flux-friendly natural-language prompt = body description
     + Digital Diorama style modifiers from `_STYLE_GUIDE.md`.
  3. Load `prompts/_flux_workflows/<workflow>.json`, substitute
     __PROMPT__ + __SEED__.
  4. POST to ComfyUI `/prompt`, poll `/history/{prompt_id}`, fetch the
     SaveImage output via `/view`, write it to
     `prompts/asset-templates/<id>/ref.png`.

This file is the canonical entry point for stage 0. The
`tools/asset_pipeline.py` orchestrator calls it via `--auto-ref` when
no per-id `ref.png` is present.

Bring-up of the ComfyUI server is documented in `tools/COMFY_RUNBOOK.md`.

Usage:
    python tools/generate_ref_image.py <asset_id> [options]

Example:
    python tools/generate_ref_image.py prop_ledger_book \\
        --workflow hero --seed 481109 --server http://localhost:8188

Exit codes:
  0  ref.png written
  1  validation failed (no template, bad workflow, bad server URL)
  2  ComfyUI submission / poll / download failed
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSET_TEMPLATES = REPO_ROOT / "prompts" / "asset-templates"
FLUX_WORKFLOWS = REPO_ROOT / "prompts" / "_flux_workflows"
STYLE_GUIDE = ASSET_TEMPLATES / "_STYLE_GUIDE.md"

COMFY_DEFAULT = "http://localhost:8188"
POLL_INTERVAL = 3   # seconds — Flux at 1024² takes ~10 s on a 5090
POLL_TIMEOUT = 600  # seconds — hero workflow at 1536²/40 steps can run ~2 min


# ---------------------------------------------------------------------------
# style-guide / prompt construction
# ---------------------------------------------------------------------------

# Digital Diorama suffix appended to every Flux prompt. Distilled from
# `prompts/asset-templates/_STYLE_GUIDE.md` (single source of truth — if you
# change this string, update the style guide first).
STYLE_SUFFIX = (
    "Photographed under overcast 5000 K diffuse daylight, neutral mid-grey "
    "seamless background, no harsh shadows, no people, no props in frame "
    "except the subject. Tactile weathered realism, hyper-realistic PBR "
    "materials with micro-bump and roughness variation, filmic desaturated "
    "palette, documentary photography aesthetic from 1994 Rwanda. "
    "Resolution at least 1024 by 1024, subject centred with 10-15 percent "
    "headroom, no watermark, no captions, no UI overlay."
)


def die(msg: str, code: int = 1) -> None:
    """Print an error to stderr and exit with the given code."""
    sys.stderr.write(f"ERROR: {msg}\n")
    sys.exit(code)


def info(msg: str) -> None:
    """Indented status line for the asset_pipeline.py log."""
    sys.stdout.write(f"  {msg}\n")


def parse_template(template_path: Path) -> tuple[dict[str, Any], str]:
    """
    Split a `<id>.md` asset template into (frontmatter dict, body text).

    The template format is the same as authored in
    `prompts/asset-templates/<id>.md`: a YAML-style frontmatter delimited
    by `---` lines, followed by the prose description.
    """
    text = template_path.read_text()
    if not text.startswith("---\n"):
        return {}, text

    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text

    fm_block = text[4:end]
    body = text[end + 5 :]

    fm: dict[str, Any] = {}
    for line in fm_block.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip()
    return fm, body


def extract_reference_section(body: str) -> str:
    """
    Pull the `## Reference image` block out of an asset template body.

    Flux prompts work best on natural-language descriptions of the photo
    we want, not modelling-time geometry instructions. The `## Reference
    image` section is authored specifically as that photo description, so
    we prefer it when present.

    The leading sentence of that section is typically a path-reference
    framer like ``prompts/.../ref.png should depict:`` — we drop it so the
    prompt starts directly with the subject description.
    """
    match = re.search(r"##\s*Reference image\s*\n(.+?)(?=\n##|\Z)", body, re.DOTALL)
    text = match.group(1).strip() if match else body.strip()
    text = re.sub(
        r"^.+?should depict:?\s*\n*",
        "",
        text,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return text.strip()


def strip_markdown(text: str) -> str:
    """Collapse markdown markers and whitespace so Flux receives prose."""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_prompt(template_path: Path) -> str:
    """
    Compose the final Flux prompt for one asset.

    Strategy: take the asset's `## Reference image` section (preferred) or
    the main body (fallback), strip markdown, append the Digital Diorama
    style suffix. Flux.1 [dev] handles long natural-language prompts well —
    no need to truncate.
    """
    _, body = parse_template(template_path)
    ref_section = extract_reference_section(body)
    base = strip_markdown(ref_section)
    return f"{base} {STYLE_SUFFIX}"


# ---------------------------------------------------------------------------
# workflow + ComfyUI
# ---------------------------------------------------------------------------


def load_workflow(workflow_name: str, prompt: str, seed: int) -> dict[str, Any]:
    """
    Load a workflow JSON and substitute prompt + seed into placeholders.

    The workflow is loaded as text first (so we can do simple string
    substitution on the placeholders) then re-parsed as JSON. This keeps
    the workflow templates valid JSON on disk while still supporting the
    two pipeline-wide placeholders.
    """
    path = FLUX_WORKFLOWS / f"{workflow_name}.json"
    if not path.exists():
        die(f"workflow not found: {path.relative_to(REPO_ROOT)}")
    raw = path.read_text()
    raw = raw.replace("__PROMPT__", json.dumps(prompt)[1:-1])
    raw = raw.replace('"__SEED__"', str(seed))
    try:
        workflow = json.loads(raw)
    except json.JSONDecodeError as exc:
        die(f"workflow JSON invalid after substitution: {exc}")
    workflow.pop("_comment", None)
    return workflow


def submit_workflow(workflow: dict[str, Any], server: str, client_id: str) -> str:
    """POST a workflow to ComfyUI and return the prompt_id for polling."""
    payload = {"prompt": workflow, "client_id": client_id}
    try:
        r = requests.post(f"{server}/prompt", json=payload, timeout=30)
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        die(f"POST /prompt failed: {exc}", code=2)
    data = r.json()
    if "prompt_id" not in data:
        die(f"no prompt_id in /prompt response: {data}", code=2)
    return data["prompt_id"]


def poll_history(prompt_id: str, server: str) -> dict[str, Any]:
    """Poll /history/{id} until ComfyUI reports outputs; return them."""
    endpoint = f"{server}/history/{prompt_id}"
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > POLL_TIMEOUT:
            die(f"Timed out after {POLL_TIMEOUT}s polling /history", code=2)
        try:
            r = requests.get(endpoint, timeout=15)
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.RequestException as exc:
            info(f"[{elapsed:6.0f}s] status fetch failed: {exc}")
            time.sleep(POLL_INTERVAL)
            continue
        if prompt_id in data:
            entry = data[prompt_id]
            outputs = entry.get("outputs") or {}
            if outputs:
                info(f"[{elapsed:6.0f}s] outputs received")
                return outputs
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                msgs = status.get("messages") or []
                die(f"ComfyUI reported error: {msgs}", code=2)
        info(f"[{elapsed:6.0f}s] pending")
        time.sleep(POLL_INTERVAL)


def find_first_image(outputs: dict[str, Any]) -> dict[str, str]:
    """Return the first {filename, subfolder, type} record across all nodes."""
    for node_outputs in outputs.values():
        for img in node_outputs.get("images", []) or []:
            return {
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
            }
    die("ComfyUI history contained no images", code=2)
    raise SystemExit(2)  # unreachable, satisfies type checker


def download_image(record: dict[str, str], server: str, dest: Path) -> None:
    """GET /view?... and write the bytes to dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    params = {
        "filename": record["filename"],
        "subfolder": record["subfolder"],
        "type": record["type"],
    }
    try:
        r = requests.get(f"{server}/view", params=params, timeout=60)
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        die(f"GET /view failed: {exc}", code=2)
    dest.write_bytes(r.content)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def existing_ref(asset_dir: Path) -> Path | None:
    """Return the first ref.* image in the asset's prompt directory, if any."""
    for ext in (".png", ".jpg", ".jpeg"):
        candidate = asset_dir / f"ref{ext}"
        if candidate.exists():
            return candidate
    return None


def health_check(server: str) -> None:
    """Ping ComfyUI's /system_stats; fail fast with a clear error if down."""
    try:
        r = requests.get(f"{server}/system_stats", timeout=5)
        r.raise_for_status()
    except requests.exceptions.RequestException as exc:
        die(
            f"ComfyUI unreachable at {server} — start it per tools/COMFY_RUNBOOK.md "
            f"(detail: {exc})",
            code=2,
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 0 — generate ref.png via ComfyUI + Flux.1 [dev].")
    parser.add_argument("asset_id", help="Snake_case asset id (must have a matching <id>.md template)")
    parser.add_argument(
        "--workflow",
        default="default",
        help="Workflow name in prompts/_flux_workflows/ (default | hero, default: default)",
    )
    parser.add_argument("--seed", type=int, default=481109, help="Flux noise seed (default 481109 — matches eucalyptus_mature)")
    parser.add_argument("--server", default=COMFY_DEFAULT, help="ComfyUI HTTP server URL (default %(default)s)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing ref.png. Without this flag, the script no-ops when ref.png exists.",
    )
    parser.add_argument(
        "--print-prompt-only",
        action="store_true",
        help="Print the composed Flux prompt and exit (no ComfyUI call). For debugging the prompt builder.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    template_path = ASSET_TEMPLATES / f"{args.asset_id}.md"
    if not template_path.exists():
        die(f"template not found: {template_path.relative_to(REPO_ROOT)}")

    asset_dir = ASSET_TEMPLATES / args.asset_id
    asset_dir.mkdir(parents=True, exist_ok=True)

    prompt = build_prompt(template_path)
    if args.print_prompt_only:
        sys.stdout.write(prompt + "\n")
        return 0

    existing = existing_ref(asset_dir)
    if existing and not args.force:
        info(f"ref already present at {existing.relative_to(REPO_ROOT)} — skipping (use --force to regenerate)")
        return 0

    info(f"asset:    {args.asset_id}")
    info(f"workflow: {args.workflow}")
    info(f"seed:     {args.seed}")
    info(f"server:   {args.server}")
    info(f"prompt:   {prompt[:140] + ('...' if len(prompt) > 140 else '')}")

    health_check(args.server)
    workflow = load_workflow(args.workflow, prompt, args.seed)
    client_id = f"witness-{uuid.uuid4().hex[:8]}"
    prompt_id = submit_workflow(workflow, args.server, client_id)
    info(f"prompt_id: {prompt_id}")

    outputs = poll_history(prompt_id, args.server)
    record = find_first_image(outputs)
    dest = asset_dir / "ref.png"
    download_image(record, args.server, dest)

    info(f"wrote {dest.relative_to(REPO_ROOT)} ({dest.stat().st_size // 1024} KB)")
    info("next: python tools/asset_pipeline.py " + args.asset_id + " --kind mesh "
         f"--image {dest.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
