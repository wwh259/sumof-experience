#!/usr/bin/env python3
"""校验经验卡是否符合 schema v1。

用法：
  python validate_card.py <文件或目录> [...]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STAGES = {
    "S1 需求分析", "S2 技术选型", "S3 工程规范", "S4 模块开发",
    "S5 测试评估", "S6 部署上线", "S7 运维迭代", "跨阶段",
}
MODULES = {"Conversation", "Knowledge", "Retrieval", "Agent", "Governance", "Platform", "通用"}
LAYERS = {"Interface", "Application", "Domain", "Infrastructure", "部署资产", "通用"}
TYPES = {"decision", "pitfall", "pattern", "constraint", "path"}
STATUS = {"active", "superseded", "deprecated"}
TRACKS = {"slow", "fast", "fact"}

# 本机绝对路径模式：命中即报错，提示写「项目名 + 相对路径」
# 盘符后紧跟正斜杠时排除，避免把 URL 的 :// 误判为盘符路径（如 https://example.com）
ABS_PATH = re.compile(r"(?:[A-Za-z]:[\\/](?![/])|/Users/|/home/|/mnt/)")

REQUIRED = ["schema_version", "id", "title", "date", "source", "background", "stage", "type", "status", "confidence", "track"]
ENTRY_FIELDS = ["坐标", "触发", "做法", "原因", "证据", "置信度", "背景"]
FAIL_FIELDS = ["坐标", "现象", "根因", "代价", "规避"]


def parse_frontmatter(lines: list[str], path: Path, errors: list[str]) -> dict[str, str]:
    if not lines or lines[0].strip() != "---":
        errors.append("缺少 frontmatter 起始 ---")
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        errors.append("frontmatter 未闭合")
        return {}
    data: dict[str, str] = {}
    for i in range(1, end):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in (" ", "\t"):
            errors.append(f"第 {i + 1} 行是多行值续行，frontmatter 单字段单行，不得换行展开")
            continue
        if ":" not in line:
            errors.append(f"第 {i + 1} 行不是 key: value")
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def check_coordinate(value: str, where: str, errors: list[str], require_type: bool = True) -> None:
    typ = ""
    if "｜类型：" in value:
        coord, typ = value.split("｜类型：", 1)
    elif require_type:
        errors.append(f"{where}: 坐标缺少「｜类型：」")
        return
    else:
        coord = value
    parts = [p.strip() for p in coord.split("/")]
    if len(parts) != 3:
        errors.append(f"{where}: 坐标应为「阶段 / 层 / 模块」")
        return
    stage, layer, module = parts
    if stage not in STAGES:
        errors.append(f"{where}: 非法阶段 {stage}")
    if layer not in LAYERS:
        errors.append(f"{where}: 非法分层 {layer}")
    if module not in MODULES:
        errors.append(f"{where}: 非法模块 {module}")
    if require_type and typ.strip() not in TYPES:
        errors.append(f"{where}: 非法类型 {typ.strip()}")


def check_block(block: list[str], fields: list[str], where: str, errors: list[str]) -> None:
    bullets = [ln for ln in block if ln.strip().startswith("- ")]
    if len(bullets) != len(fields):
        errors.append(f"{where}: 字段数 {len(bullets)}，应为 {len(fields)}")
        return
    keys = []
    for ln in bullets:
        body = ln.strip()[2:]
        if "：" not in body:
            errors.append(f"{where}: 字段缺少全角冒号: {body[:12]}")
            return
        keys.append(body.split("：", 1)[0].strip())
    if keys != fields:
        errors.append(f"{where}: 字段顺序应为 {fields}，实际 {keys}")


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return [f"无法读取: {exc}"]
    lines = text.splitlines()
    if len(lines) > 150:
        errors.append(f"超过 150 行（{len(lines)}）")

    for i, ln in enumerate(lines):
        if ABS_PATH.search(ln):
            errors.append(f"第 {i + 1} 行含本机绝对路径，应写「项目名 + 相对路径」: {ln.strip()[:40]}")
            break

    fm = parse_frontmatter(lines, path, errors)
    for key in REQUIRED:
        if not fm.get(key):
            errors.append(f"缺少必填字段 {key}")

    if fm.get("schema_version") and fm["schema_version"] != "1":
        errors.append(f"未知 schema_version: {fm['schema_version']}")
    if fm.get("id") and fm["id"] != path.stem:
        errors.append(f"id 与文件名不一致: {fm['id']} != {path.stem}")
    if fm.get("title") and len(fm["title"]) > 20:
        errors.append(f"title 超过 20 字（{len(fm['title'])} 字）: {fm['title']}")
    if fm.get("date") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fm["date"]):
        errors.append(f"date 格式错误: {fm['date']}")
    if fm.get("tags"):
        m = re.fullmatch(r"\[(.*)\]", fm["tags"])
        if not m:
            errors.append(f"tags 应为行内列表 [a, b]: {fm['tags']}")
        else:
            tags = [t.strip() for t in m.group(1).split(",") if t.strip()]
            if not 2 <= len(tags) <= 5:
                errors.append(f"tags 数量 {len(tags)} 个，应为 2–5 个")
    if fm.get("track") and fm["track"] not in TRACKS:
        errors.append(f"非法 track: {fm['track']}（取值 slow / fast / fact）")
    if fm.get("stage") and fm["stage"] not in STAGES:
        errors.append(f"非法 stage: {fm['stage']}")
    if fm.get("module") and fm["module"] not in MODULES:
        errors.append(f"非法 module: {fm['module']}")
    if fm.get("layer") and fm["layer"] not in LAYERS:
        errors.append(f"非法 layer: {fm['layer']}")
    if fm.get("type") and fm["type"] not in TYPES:
        errors.append(f"非法 type: {fm['type']}")
    if fm.get("status") and fm["status"] not in STATUS:
        errors.append(f"非法 status: {fm['status']}")
    if fm.get("confidence"):
        try:
            value = float(fm["confidence"])
            if not 0.3 <= value <= 0.9:
                errors.append(f"confidence 越界: {value}")
        except ValueError:
            errors.append(f"confidence 不是数字: {fm['confidence']}")
    if fm.get("status") == "superseded" and not fm.get("superseded_by"):
        errors.append("status=superseded 但 superseded_by 为空")

    headers = {ln.strip() for ln in lines if ln.startswith("## ")}
    for num in ("1", "2", "4", "5"):
        if not any(h.startswith(f"## {num}.") for h in headers):
            errors.append(f"缺少第 {num} 节")

    entries = [i for i, ln in enumerate(lines) if re.match(r"^### E\d+ ", ln)]
    if len(entries) > 10:
        errors.append(f"经验条目 {len(entries)} 条，上限 10")
    for idx, start in enumerate(entries):
        end = entries[idx + 1] if idx + 1 < len(entries) else next(
            (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines)
        )
        block = [ln for ln in lines[start + 1:end] if ln.strip()]
        where = lines[start].strip()
        check_block(block, ENTRY_FIELDS, where, errors)
        for ln in block:
            if ln.strip().startswith("- 坐标："):
                check_coordinate(ln.strip()[len("- 坐标："):], where, errors)

    fails = [i for i, ln in enumerate(lines) if re.match(r"^### F\d+ ", ln)]
    if len(fails) > 5:
        errors.append(f"失败反例 {len(fails)} 条，上限 5")
    for idx, start in enumerate(fails):
        end = fails[idx + 1] if idx + 1 < len(fails) else next(
            (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines)
        )
        block = [ln for ln in lines[start + 1:end] if ln.strip()]
        where = lines[start].strip()
        check_block(block, FAIL_FIELDS, where, errors)
        for ln in block:
            if ln.strip().startswith("- 坐标："):
                check_coordinate(ln.strip()[len("- 坐标："):], where, errors, require_type=False)

    return errors


def collect(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(p for p in target.glob("*.md") if not p.name.startswith("."))
    return [target]


def main() -> None:
    parser = argparse.ArgumentParser(description="校验经验卡 schema v1")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()

    total = 0
    bad = 0
    for target in args.paths:
        for path in collect(Path(target)):
            total += 1
            errors = validate(path)
            if errors:
                bad += 1
                print(f"FAIL {path}")
                for err in errors:
                    print(f"  - {err}")
            else:
                print(f"PASS {path}")

    print(f"\n{total} 个文件，{bad} 个失败")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
