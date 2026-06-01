"""
将 docs/skills/skill-mini-map.json 中的技能 / 特性数据导入 PostgreSQL。

字典结构（扁平 dict，key 为技能 id）：
    {
      "200000": {"cost": "0", "desc": "...", "families": "SDT_NONE", "name": "GM被动", "power": "0"},
      ...
    }

分流规则：
- families == "SDT_NONE"  -> 特性，写入 pokemon_trait
      name -> pokemon_trait.name
      desc -> pokemon_trait.description
- families != "SDT_NONE"  -> 技能，写入 skill
      families -> 根据 attribute.name 查 attribute.id 作为 skill.attr_id
      name     -> skill.name
      power    -> skill.power
      cost     -> skill.consume
      desc     -> skill.skill_desc
      icon     -> 从 https://game.gtimg.cn/images/rocom/rocodata/skill/<key>.png 下载，
                  上传到自有 OSS 后写入 skill.icon。图片 404（或下载失败）时打印日志，
                  新增数据不入库；已存在数据（--update 模式）则保留原 icon。

写入策略（核心需求）：
- 默认：只新增没有的数据（按 name 判定是否已存在），已有数据不修改。
- --update true：已存在的数据也进行更新。

用法：
    uv run python scripts/import_skills_traits.py                 # 仅新增
    uv run python scripts/import_skills_traits.py --update true   # 新增 + 更新已有
    uv run python scripts/import_skills_traits.py --dry-run       # 预览，不下载/不写库
    uv run python scripts/import_skills_traits.py --limit 10      # 只处理前 N 条（调试）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import PG_CONFIG
from oss.oss import COSClient

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "docs" / "skills" / "skill-mini-map.json"

TRAIT_FAMILY = "SDT_NONE"
SKILL_ICON_URL_TMPL = "https://game.gtimg.cn/images/rocom/rocodata/skill/{key}.png"
SKILL_ICON_OSS_PREFIX = "skill/icon"


def _str2bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t", "on"}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    text = _clean(value)
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _derive_skill_type(desc: str) -> str:
    """根据技能描述推断 skill.type：魔攻 / 物攻 / 空（其余手动优化）。"""
    if "造成魔法伤害" in desc or "造成魔伤" in desc:
        return "魔攻"
    if "造成物理伤害" in desc or "造成物伤" in desc:
        return "物攻"
    return ""


def _pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def _load_entries() -> list[tuple[str, dict[str, Any]]]:
    if not JSON_PATH.exists():
        raise FileNotFoundError(f"未找到字典文件：{JSON_PATH}")
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("字典文件顶层应为 dict（key 为技能 id）")
    # 按数值 key 排序，输出更稳定
    return sorted(payload.items(), key=lambda kv: _to_int(kv[0]))


def _load_attr_map(cur) -> dict[str, int]:
    cur.execute("SELECT name, id FROM attribute")
    return {row[0]: row[1] for row in cur.fetchall()}


def _load_name_set(cur, table: str) -> set[str]:
    cur.execute(f"SELECT name FROM {table}")
    return {row[0] for row in cur.fetchall()}


def _fetch_icon_bytes(key: str) -> bytes | None:
    """下载技能图标；404 或下载失败返回 None。"""
    url = SKILL_ICON_URL_TMPL.format(key=key)
    try:
        resp = requests.get(url, timeout=15)
    except requests.RequestException as exc:
        print(f"    [warn] 图标下载异常 key={key} url={url} err={exc}", flush=True)
        return None
    if resp.status_code == 404:
        print(f"    [warn] 图标 404，跳过 key={key} url={url}", flush=True)
        return None
    if resp.status_code != 200 or not resp.content:
        print(
            f"    [warn] 图标不可用 key={key} status={resp.status_code} url={url}",
            flush=True,
        )
        return None
    return resp.content


def main() -> None:
    parser = argparse.ArgumentParser(description="导入技能/特性字典到 PostgreSQL")
    parser.add_argument(
        "--update",
        nargs="?",
        const=True,
        default=False,
        type=_str2bool,
        help="是否更新已存在数据：默认 false（仅新增），传 --update true 则更新已有",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要做的操作，不下载图片、不写库",
    )
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 条（调试用）")
    args = parser.parse_args()

    entries = _load_entries()
    if args.limit:
        entries = entries[: args.limit]

    print(
        f"[info] mode={'DRY-RUN' if args.dry_run else 'WRITE'} "
        f"update={args.update} 待处理={len(entries)} 来源={JSON_PATH}",
        flush=True,
    )

    cos = COSClient() if not args.dry_run else None

    conn = _pg_conn()
    conn.autocommit = True  # 逐条提交，单条失败不影响其它行
    try:
        with conn.cursor() as cur:
            attr_map = _load_attr_map(cur)
            trait_names = _load_name_set(cur, "pokemon_trait")
            skill_names = _load_name_set(cur, "skill")

        stats = {
            "trait_insert": 0,
            "trait_update": 0,
            "trait_skip": 0,
            "skill_insert": 0,
            "skill_update": 0,
            "skill_skip": 0,
            "skip_no_attr": 0,
            "skip_no_icon": 0,
            "fail": 0,
        }

        with conn.cursor() as cur:
            for key, item in entries:
                families = _clean(item.get("families"))
                name = _clean(item.get("name"))
                desc = _clean(item.get("desc"))
                if not name:
                    print(f"    [warn] key={key} 无 name，跳过", flush=True)
                    continue

                try:
                    if families == TRAIT_FAMILY:
                        _handle_trait(cur, name, desc, trait_names, args, stats)
                    else:
                        _handle_skill(
                            cur, key, item, families, name, desc,
                            skill_names, attr_map, cos, args, stats,
                        )
                except Exception as exc:  # noqa: BLE001 —— 单行容错，继续后续
                    stats["fail"] += 1
                    print(f"    [fail] key={key} name={name!r} err={exc}", flush=True)
    finally:
        conn.close()

    print("\n[summary]", flush=True)
    print(
        f"  特性  新增={stats['trait_insert']} 更新={stats['trait_update']} "
        f"跳过={stats['trait_skip']}",
        flush=True,
    )
    print(
        f"  技能  新增={stats['skill_insert']} 更新={stats['skill_update']} "
        f"跳过={stats['skill_skip']}",
        flush=True,
    )
    print(
        f"  其它  无对应属性跳过={stats['skip_no_attr']} "
        f"图标缺失跳过={stats['skip_no_icon']} 失败={stats['fail']}",
        flush=True,
    )


def _handle_trait(cur, name, desc, trait_names, args, stats) -> None:
    exists = name in trait_names
    if exists and not args.update:
        stats["trait_skip"] += 1
        return

    if args.dry_run:
        action = "update" if exists else "insert"
        print(f"    [dry-run] trait {action} name={name!r}", flush=True)
        stats["trait_update" if exists else "trait_insert"] += 1
        return

    if exists:
        cur.execute(
            "UPDATE pokemon_trait SET description = %s WHERE name = %s",
            (desc, name),
        )
        stats["trait_update"] += 1
    else:
        cur.execute(
            "INSERT INTO pokemon_trait (name, description) VALUES (%s, %s)",
            (name, desc),
        )
        trait_names.add(name)
        stats["trait_insert"] += 1


def _handle_skill(
    cur, key, item, families, name, desc,
    skill_names, attr_map, cos, args, stats,
) -> None:
    attr_id = attr_map.get(families)
    if attr_id is None:
        print(
            f"    [warn] key={key} name={name!r} 属性 {families!r} 未匹配 attribute，跳过",
            flush=True,
        )
        stats["skip_no_attr"] += 1
        return

    exists = name in skill_names
    if exists and not args.update:
        stats["skill_skip"] += 1
        return

    power = _to_int(item.get("power"))
    consume = _to_int(item.get("cost"))
    skill_type = _derive_skill_type(desc)

    if args.dry_run:
        action = "update" if exists else "insert"
        print(
            f"    [dry-run] skill {action} name={name!r} attr={families}({attr_id}) "
            f"power={power} consume={consume} type={skill_type or '-'} icon<-{key}.png",
            flush=True,
        )
        stats["skill_update" if exists else "skill_insert"] += 1
        return

    # 下载并上传图标
    icon_bytes = _fetch_icon_bytes(key)
    icon_url: str | None = None
    if icon_bytes is not None:
        icon_url = cos.upload_bytes(
            icon_bytes, filename=f"{key}.png", prefix=SKILL_ICON_OSS_PREFIX
        )
    elif not exists:
        # 新增且图标缺失 -> 按需求不入库
        stats["skip_no_icon"] += 1
        return
    # 已存在且图标缺失 -> 保留原 icon，仅更新其它字段

    if exists:
        if icon_url is not None:
            cur.execute(
                """
                UPDATE skill
                SET attr_id = %s, power = %s, consume = %s, type = %s,
                    skill_desc = %s, icon = %s
                WHERE name = %s
                """,
                (attr_id, power, consume, skill_type, desc, icon_url, name),
            )
        else:
            cur.execute(
                """
                UPDATE skill
                SET attr_id = %s, power = %s, consume = %s, type = %s, skill_desc = %s
                WHERE name = %s
                """,
                (attr_id, power, consume, skill_type, desc, name),
            )
        stats["skill_update"] += 1
    else:
        cur.execute(
            """
            INSERT INTO skill (name, attr_id, power, consume, type, skill_desc, icon)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (name, attr_id, power, consume, skill_type, desc, icon_url or ""),
        )
        skill_names.add(name)
        stats["skill_insert"] += 1


if __name__ == "__main__":
    main()
