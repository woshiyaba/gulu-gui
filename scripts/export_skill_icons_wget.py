"""
导出 skill 表所有技能图标的完整 URL，生成一个可在服务器运行的 wget 备份脚本。

URL 拼接规则与 api/utils/media.py 的 build_image_url 完全一致：
    - 空值跳过
    - 已是 http(s) 开头则原样使用
    - 否则把文件名前的 "数字_" 前缀去掉后，再拼 BASE_URL

用法：
    uv run python scripts/export_skill_icons_wget.py
    uv run python scripts/export_skill_icons_wget.py --output backup_skill_icons.sh
    uv run python scripts/export_skill_icons_wget.py --dest /var/backup/skill_icons
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

from config import BASE_URL, PG_CONFIG


def build_image_url(path: str) -> str:
    if not path:
        return ""
    if path.startswith("http"):
        return path
    dir_part, _, filename = path.rpartition("/")
    if "_" in filename:
        filename = filename.split("_", 1)[1]
    clean_path = f"{dir_part}/{filename}"
    return f"{BASE_URL}{clean_path}"


def fetch_skill_icons() -> list[tuple[str, str, str]]:
    """返回 [(技能名, 原始 icon, 拼接后的完整 URL), ...]，按完整 URL 去重。"""
    conn = psycopg2.connect(**PG_CONFIG)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT name, icon FROM skill ORDER BY name")
            rows = cur.fetchall()
    finally:
        conn.close()

    seen: set[str] = set()
    result: list[tuple[str, str, str]] = []
    skipped_empty = 0
    for row in rows:
        raw = (row.get("icon") or "").strip()
        url = build_image_url(raw)
        if not url:
            skipped_empty += 1
            continue
        if url in seen:
            continue
        seen.add(url)
        result.append((row["name"], raw, url))

    print(
        f"[info] 共 {len(rows)} 条技能；空 icon {skipped_empty} 条；"
        f"去重后待下载 {len(result)} 条",
        flush=True,
    )
    return result


def render_shell(items: list[tuple[str, str, str]], default_dest: str) -> str:
    lines: list[str] = [
        "#!/usr/bin/env bash",
        "# 自动生成：技能图标备份下载脚本",
        f"# 共 {len(items)} 个图标",
        "set -euo pipefail",
        "",
        f'DEST_DIR="${{1:-{default_dest}}}"',
        'mkdir -p "$DEST_DIR"',
        'cd "$DEST_DIR"',
        "",
        "# -x 保留远端目录；-nH 去掉主机名层；-nc 已存在则跳过（断点续传）",
        "WGET_OPTS=(-x -nH -nc --tries=3 --timeout=20)",
        "",
    ]
    for name, _raw, url in items:
        lines.append(f"# {name}")
        lines.append(f'wget "${{WGET_OPTS[@]}}" "{url}"')
    lines.append("")
    lines.append('echo "[done] 备份目录：$DEST_DIR"')
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成技能图标 wget 备份脚本")
    parser.add_argument(
        "--output", "-o",
        default="backup_skill_icons.sh",
        help="输出的 shell 脚本路径（默认 backup_skill_icons.sh）",
    )
    parser.add_argument(
        "--dest",
        default="./skill_icons_backup",
        help="生成的 sh 脚本默认下载目录（运行 sh 时可用第一个位置参数覆盖）",
    )
    args = parser.parse_args()

    items = fetch_skill_icons()
    if not items:
        print("[warn] 未查到任何技能图标 URL", file=sys.stderr)
        return 1

    content = render_shell(items, default_dest=args.dest)
    out = Path(args.output).resolve()
    out.write_text(content, encoding="utf-8", newline="\n")
    print(f"[ok] 已生成 {out}（{len(items)} 条 wget 指令）")
    print('[hint] 服务器上运行： bash backup_skill_icons.sh  或  bash backup_skill_icons.sh /your/dest')
    return 0


if __name__ == "__main__":
    sys.exit(main())
