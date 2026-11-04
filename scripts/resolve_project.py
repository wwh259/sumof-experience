#!/usr/bin/env python3
"""解析知识库位置与项目级经验目录。

用法：
  python resolve_project.py                 # 解析当前目录
  python resolve_project.py --cwd <路径>    # 解析指定目录
  python resolve_project.py --init <知识库路径>  # 首次写入配置并解析

输出：单行 JSON。status=needs_config 表示必须先配置知识库路径。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_HOME = Path.home() / ".sumof-experience"
DEFAULT_KB = Path("D:/Knowledge-base") if os.name == "nt" else Path.home() / "Knowledge-base"


def home_dir() -> Path:
    home = os.environ.get("SUM_OF_EXPERIENCE_HOME") or str(DEFAULT_HOME)
    return Path(home).expanduser().resolve()


def config_path() -> Path:
    return home_dir() / "config.json"


def git(cwd: Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def normalize_remote(url: str) -> str:
    """把任意 git remote 归一化为 host/owner/repo。"""
    u = url.strip()
    if not u:
        return ""
    if "://" in u:
        u = u.split("://", 1)[1]
    if "@" in u:
        u = u.split("@", 1)[1]
    if ":" in u:
        host, rest = u.split(":", 1)
        if "/" not in host and rest[:1] and not rest[:1].isdigit():
            u = host + "/" + rest
    u = u.rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    return u.lower()


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "unnamed"


def short_hash(text: str, size: int = 6) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:size]


def build_slug(remote: str, relpath: str, root: Path, is_git: bool) -> str:
    parts: list[str] = []
    if remote:
        segments = [p for p in remote.split("/") if p]
        # 首段是 host，其余全部保留，避免 GitLab 多级 group 被截断
        parts.extend(segments[1:] if len(segments) > 1 else segments)
        if relpath:
            parts.extend(relpath.split("/"))
    elif is_git:
        parts.extend([root.name, *relpath.split("/")] if relpath else [root.name])
        parts[-1] = f"{parts[-1]}--{short_hash(str(root))}"
    else:
        parts.extend([root.name, short_hash(str(root))])
    slug = "__".join(slugify(p) for p in parts)
    return slug[:90]


def detect_project(cwd: Path) -> dict:
    repo_root = git(cwd, "rev-parse", "--show-toplevel")
    if repo_root:
        root = Path(repo_root).resolve()
        relpath = os.path.relpath(str(cwd), str(root)).replace("\\", "/")
        relpath = "" if relpath == "." else relpath
        remote = normalize_remote(git(cwd, "config", "--get", "remote.origin.url"))
        identity = "git-remote" if remote else "git-local"
        return {"root": root, "relpath": relpath, "remote": remote, "identity": identity}
    root = cwd.resolve()
    return {"root": root, "relpath": "", "remote": "", "identity": "filesystem"}


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_config(kb_path: Path) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "kb_path": str(kb_path)}
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_if_changed(path: Path, text: str) -> bool:
    """内容相同时不写，避免知识库 git 仓库产生无意义 diff。"""
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == text:
                return False
        except OSError:
            pass
    path.write_text(text, encoding="utf-8")
    return True


def update_registry(kb: Path, slug: str, info: dict) -> bool:
    """登记项目；返回是否首次创建。"""
    registry_path = kb / ".registry.json"
    registry = {"version": 1, "projects": {}}
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    projects = registry.setdefault("projects", {})
    created = slug not in projects
    entry = projects.setdefault(
        slug,
        {
            "id": slug,
            "remote": info["remote"],
            "relpath": info["relpath"],
            "identity": info["identity"],
            "aliases": [],
        },
    )
    entry["remote"] = info["remote"] or entry.get("remote", "")
    entry["relpath"] = info["relpath"]
    entry["identity"] = info["identity"]
    write_if_changed(
        registry_path,
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
    )
    return created


def emit(payload: dict, code: int = 0) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def main() -> None:
    parser = argparse.ArgumentParser(description="解析项目级经验目录")
    parser.add_argument("--cwd", default=os.getcwd(), help="项目目录，默认当前目录")
    parser.add_argument(
        "--init",
        nargs="?",
        const=str(DEFAULT_KB),
        metavar="KB_PATH",
        help=f"首次配置知识库路径；省略时使用默认 {DEFAULT_KB}",
    )
    args = parser.parse_args()

    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.is_dir():
        emit({"status": "error", "message": f"目录不存在: {cwd}"}, 1)

    env_kb = os.environ.get("SUM_OF_EXPERIENCE_KB", "").strip()
    config_path_ = config_path()

    if args.init:
        kb = Path(args.init).expanduser()
        if not kb.is_absolute():
            emit({"status": "error", "message": "知识库路径必须是绝对路径"}, 1)
        kb.mkdir(parents=True, exist_ok=True)
        write_config(kb.resolve())
    elif env_kb:
        write_config(Path(env_kb).expanduser().resolve())
    elif not load_config().get("kb_path"):
        emit(
            {
                "status": "needs_config",
                "config_path": str(config_path_),
                "default_kb_path": str(DEFAULT_KB),
                "message": "未配置知识库路径。询问用户使用默认路径还是指定其它路径，然后执行 --init。",
            },
            2,
        )

    kb = Path(load_config()["kb_path"]).expanduser().resolve()
    if not kb.is_dir():
        emit({"status": "error", "message": f"知识库目录不存在: {kb}"}, 1)

    info = detect_project(cwd)
    slug = build_slug(info["remote"], info["relpath"], info["root"], info["identity"].startswith("git"))
    project_dir = kb / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    cards_dir = project_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    created = update_registry(kb, slug, info)
    write_if_changed(
        project_dir / ".project.json",
        json.dumps(
            {
                "id": slug,
                "remote": info["remote"],
                "relpath": info["relpath"],
                "identity": info["identity"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )

    emit(
        {
            "status": "ok",
            "kb_path": str(kb),
            "project_id": slug,
            "project_dir": str(project_dir),
            "cards_dir": str(cards_dir),
            "remote": info["remote"],
            "relpath": info["relpath"],
            "identity": info["identity"],
            "created": created,
        }
    )


if __name__ == "__main__":
    main()
