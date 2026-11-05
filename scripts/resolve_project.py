#!/usr/bin/env python3
"""解析知识库位置与项目级经验目录。

输出目录固定为 <KB>/experience/<项目>/；项目键以知识库台账为准，
保证与 <KB>/raw/<项目>/ 以及 digital_twin 的归纳结果对得上。

用法：
  python resolve_project.py --cwd <项目目录>
  python resolve_project.py --init "<用户指定的知识库绝对路径>"
  python resolve_project.py --show          # 只看当前配置，不创建目录

输出：单行 JSON。status=needs_config 表示必须先配置知识库路径。
本脚本不写知识库台账、不建索引、不执行 git 操作。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_HOME = Path.home() / ".sumof-experience"
DEFAULT_KB = Path("D:/Knowledge-base") if os.name == "nt" else Path.home() / "Knowledge-base"
EXPERIENCE_DIR = "experience"
INVALID_NAME = re.compile(r'[<>:"/\\|?*]')


def home_dir() -> Path:
    return Path(os.environ.get("SUM_OF_EXPERIENCE_HOME") or str(DEFAULT_HOME)).expanduser().resolve()


def config_path() -> Path:
    return home_dir() / "config.json"


def load_config() -> dict:
    p = config_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_config(kb_path: Path) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"version": 1, "kb_path": str(kb_path)},
                            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_origin(cwd: Path) -> str:
    try:
        out = subprocess.run(["git", "config", "--get", "remote.origin.url"],
                             cwd=str(cwd), capture_output=True, text=True, timeout=8)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def kb_projects(kb: Path) -> list[str]:
    """知识库台账里的项目名集合，作为项目键的单一事实来源。"""
    p = kb / "_index.json"
    if not p.is_file():
        return []
    try:
        idx = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return sorted({str(r.get("project", "")).strip()
                   for r in idx.values() if isinstance(r, dict) and r.get("project")})


def resolve_project_name(cwd: Path, kb: Path) -> tuple[str, str]:
    """优先用台账里与 cwd 路径段同名的项目名；否则用 cwd 目录名。

    台账里的名字是 raw/<项目>/ 的真实目录名，直接复用即可，不再另造 slug。
    """
    known = {name.lower(): name for name in kb_projects(kb)}
    for part in reversed(cwd.parts):
        if part.lower() in known:
            return known[part.lower()], "kb-index"
    name = cwd.name or "unnamed"
    return INVALID_NAME.sub("-", name), "cwd-name"


def existing_sources(exp_dir: Path) -> list[dict]:
    """收集该项目已有卡的 frontmatter source，供写卡前查重。

    卡片只追加不可变，重复抽取无法覆盖修正，所以查重必须前置。
    """
    out: list[dict] = []
    if not exp_dir.is_dir():
        return out
    for card in sorted(exp_dir.glob("*.md")):
        try:
            lines = card.read_text(encoding="utf-8-sig").splitlines()[:40]
        except OSError:
            continue
        if not lines or lines[0].strip() != "---":
            continue
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if line.startswith("source:"):
                out.append({"card": card.name, "source": line.split(":", 1)[1].strip()})
                break
    return out


def emit(payload: dict, code: int = 0) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(code)


def main() -> None:
    ap = argparse.ArgumentParser(description="解析知识库与项目级经验目录")
    ap.add_argument("--cwd", default=os.getcwd(), help="项目目录，默认当前目录")
    ap.add_argument("--init", nargs="?", const=str(DEFAULT_KB), metavar="KB_PATH",
                    help=f"首次配置知识库路径；省略时使用默认 {DEFAULT_KB}")
    ap.add_argument("--show", action="store_true", help="只输出当前配置，不创建目录")
    args = ap.parse_args()

    if args.show:
        cfg = load_config()
        emit({"status": "ok" if cfg.get("kb_path") else "needs_config",
              "config_path": str(config_path()),
              "kb_path": cfg.get("kb_path", ""),
              "default_kb_path": str(DEFAULT_KB)})

    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.is_dir():
        emit({"status": "error", "message": f"目录不存在: {cwd}"}, 1)

    if args.init:
        kb = Path(args.init).expanduser()
        if not kb.is_absolute():
            emit({"status": "error", "message": "知识库路径必须是绝对路径"}, 1)
        kb.mkdir(parents=True, exist_ok=True)
        write_config(kb.resolve())
    elif os.environ.get("SUM_OF_EXPERIENCE_KB", "").strip():
        env_kb = Path(os.environ["SUM_OF_EXPERIENCE_KB"].strip()).expanduser().resolve()
        write_config(env_kb)
    elif not load_config().get("kb_path"):
        emit({"status": "needs_config",
              "config_path": str(config_path()),
              "default_kb_path": str(DEFAULT_KB),
              "message": "未配置知识库路径。询问用户用默认路径还是指定真实知识库路径，确认后执行 --init <路径>，再重跑解析。"}, 2)

    kb = Path(load_config()["kb_path"]).expanduser().resolve()
    if not kb.is_dir():
        emit({"status": "error", "message": f"知识库目录不存在: {kb}"}, 1)

    layout = {"raw_dir": (kb / "raw").is_dir(),
              "index": (kb / "_index.json").is_file(),
              "experience_dir": (kb / EXPERIENCE_DIR).is_dir()}
    warning = ""
    if not layout["raw_dir"] and not layout["index"]:
        warning = "该目录不像是 knowledge_base（缺 raw/ 与 _index.json）；仍可写入，但项目名无法与台账对齐"

    exp_root = kb / EXPERIENCE_DIR
    exp_root.mkdir(parents=True, exist_ok=True)
    project, project_source = resolve_project_name(cwd, kb)
    exp_dir = exp_root / project
    exp_dir.mkdir(parents=True, exist_ok=True)

    emit({"status": "ok",
          "kb_path": str(kb),
          "project": project,
          "project_source": project_source,
          "experience_dir": str(exp_dir),
          "remote": git_origin(cwd),
          "existing_sources": existing_sources(exp_dir),
          "kb_layout": layout,
          "warning": warning})


if __name__ == "__main__":
    main()
