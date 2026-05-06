"""
从小黑盒（xiaoheihe）egg/list 接口同步精灵蛋数据到 PostgreSQL.pokemon_egg。

字段映射（egg/list -> pokemon_egg）：
- id              -> source_id（唯一键，用于 upsert）
- name            -> name
- form            -> form
- icon            -> icon
- related_pet_id  -> pokemon_source_id
- item_quality    -> item_quality
- 经 pokemon.source_id 反查得到 -> pokemon_id（未提供 related_pet_id 或反查不到时，pokemon_id 留空，记录依然落库）

增量策略：以 source_id 为唯一键 UPSERT，已存在记录只更新不重复插入。

用法：
    uv run python scripts/import_pokemon_egg.py
    uv run python scripts/import_pokemon_egg.py --dry-run
    uv run python scripts/import_pokemon_egg.py --cache-list docs/xiaoheihe/eggs/list.json
    uv run python scripts/import_pokemon_egg.py --from-cache docs/xiaoheihe/eggs/list.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras
import requests

from config import PG_CONFIG


LIST_URL = "https://api.xiaoheihe.cn/game/roco_kingdom/egg/list"
PAGE_SIZE = 20

LIST_QUERY = {
    "app": "heybox",
    "heybox_id": "90642164",
    "os_type": "web",
    "x_app": "heybox",
    "x_client_type": "web",
    "x_os_type": "iOS",
    "x_client_version": "1.3.386",
    "version": "999.0.4",
    "hkey": "Y777X98",
    "_time": "1777442086",
    "nonce": "24A793EC14C799DCC9AA57C2210CB4FF",
}

COMMON_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://web.xiaoheihe.cn",
    "Referer": "https://web.xiaoheihe.cn/",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    ),
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
}

COOKIE_HEADER = (
    "x_xhh_tokenid=BCKby6EN7XeYN/Bly/AWZhMWBFZFC4dBAekMrq38obz/s+3hqaZXaNYAqg52KR6qsv1mcy7ZtW7ivrUxfFl+9Ew==;"
    " x_heybox_id=90642164;"
    " x_pkey=MTc2MzUzMjQxNi40N185MDY0MjE2NHZjeWVpc3hzaHdqY2lxaWw__;"
    " user_heybox_id=90642164;"
    " user_pkey=MTc2MzUzMjQxNi40N185MDY0MjE2NHZjeWVpc3hzaHdqY2lxaWw__"
)


DDL = """
CREATE TABLE IF NOT EXISTS pokemon_egg (
    id                SERIAL PRIMARY KEY,
    source_id         BIGINT       NOT NULL,
    name              VARCHAR(100) NOT NULL DEFAULT '',
    form              VARCHAR(100) NOT NULL DEFAULT '',
    icon              VARCHAR(500) NOT NULL DEFAULT '',
    pokemon_source_id BIGINT,
    pokemon_id        INT,
    item_quality      SMALLINT     NOT NULL DEFAULT 0,
    created_at        TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_pe_source_id UNIQUE (source_id)
);

CREATE INDEX IF NOT EXISTS idx_pe_pokemon_source_id ON pokemon_egg (pokemon_source_id);
CREATE INDEX IF NOT EXISTS idx_pe_pokemon_id ON pokemon_egg (pokemon_id);
CREATE INDEX IF NOT EXISTS idx_pe_item_quality ON pokemon_egg (item_quality);
CREATE INDEX IF NOT EXISTS idx_pe_name ON pokemon_egg (name);
"""


def _ensure_utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _clean_str(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(COMMON_HEADERS)
    session.headers["Cookie"] = COOKIE_HEADER
    return session


def fetch_egg_list(session: requests.Session) -> list[dict[str, Any]]:
    eggs: list[dict[str, Any]] = []
    offset = 0
    while True:
        body = {"q": "", "offset": str(offset), "limit": str(PAGE_SIZE)}
        resp = session.post(
            LIST_URL,
            params=LIST_QUERY,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "ok":
            raise RuntimeError(f"egg/list 返回异常: {payload}")
        chunk = (payload.get("result") or {}).get("list") or []
        eggs.extend(chunk)
        print(f"    [list] offset={offset} got={len(chunk)} total={len(eggs)}", flush=True)
        if len(chunk) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.2)
    return eggs


def _normalize_eggs(raw: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """以 source_id 去重，返回排序后的 rows。"""
    merged: dict[int, dict[str, Any]] = {}
    warnings: list[str] = []
    for item in raw:
        source_id = _to_int(item.get("id"))
        if source_id is None:
            warnings.append(f"[warn] 无效 egg id，已跳过：{item!r}")
            continue
        merged[source_id] = {
            "source_id": source_id,
            "name": _clean_str(item.get("name")),
            "form": _clean_str(item.get("form")),
            "icon": _clean_str(item.get("icon")),
            "pokemon_source_id": _to_int(item.get("related_pet_id")),
            "item_quality": _to_int(item.get("item_quality")) or 0,
        }
    rows = [merged[k] for k in sorted(merged.keys())]
    return rows, warnings


def _resolve_pokemon_ids(
    cur, rows: list[dict[str, Any]]
) -> dict[str, list[str]]:
    """根据 pokemon_source_id 反查 pokemon.id，写入 row['pokemon_id']。

    匹配不到时 pokemon_id 留 None，记录仍会落库（只是不进行关联）。
    返回分类后的提示信息：no_related / not_found / ambiguous。
    """
    source_ids = sorted({row["pokemon_source_id"] for row in rows if row["pokemon_source_id"] is not None})
    mapping: dict[int, list[int]] = {}
    if source_ids:
        cur.execute(
            "SELECT id, source_id FROM pokemon WHERE source_id = ANY(%s)",
            (source_ids,),
        )
        for row in cur.fetchall():
            mapping.setdefault(int(row["source_id"]), []).append(int(row["id"]))

    notes: dict[str, list[str]] = {
        "no_related": [],
        "not_found": [],
        "ambiguous": [],
    }
    for row in rows:
        psid = row["pokemon_source_id"]
        if psid is None:
            row["pokemon_id"] = None
            notes["no_related"].append(
                f"egg source_id={row['source_id']} name={row['name']!r} 未提供 related_pet_id（仍落库，pokemon_id=NULL）"
            )
            continue
        candidates = mapping.get(psid) or []
        if not candidates:
            row["pokemon_id"] = None
            notes["not_found"].append(
                f"egg source_id={row['source_id']} name={row['name']!r} "
                f"related_pet_id={psid} 在 pokemon.source_id 中查无（仍落库，pokemon_id=NULL）"
            )
            continue
        if len(candidates) > 1:
            notes["ambiguous"].append(
                f"egg source_id={row['source_id']} name={row['name']!r} "
                f"related_pet_id={psid} 命中多个 pokemon.id={candidates}，取第一个"
            )
        row["pokemon_id"] = candidates[0]
    return notes


def _pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(**PG_CONFIG)


def main() -> None:
    _ensure_utf8_stdout()

    parser = argparse.ArgumentParser(description="同步 xiaoheihe egg 数据到 PostgreSQL.pokemon_egg")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正写库")
    parser.add_argument(
        "--cache-list",
        type=str,
        default=None,
        help="若指定，则把 egg/list 全量结果写入该 JSON 文件（用于排查）",
    )
    parser.add_argument(
        "--from-cache",
        type=str,
        default=None,
        help="若指定，则跳过 egg/list 调用，直接读取该 JSON 文件",
    )
    args = parser.parse_args()

    total_start = time.time()
    print("=" * 60)
    print("  同步 xiaoheihe egg 数据 → PostgreSQL.pokemon_egg")
    print(f"  dry_run={args.dry_run}")
    print("=" * 60)

    if args.from_cache:
        cache_path = Path(args.from_cache).expanduser().resolve()
        print(f"\n[>>] 加载 egg 缓存: {cache_path}", flush=True)
        loaded = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw_eggs = ((loaded.get("result") or {}).get("list")) or []
        else:
            raw_eggs = loaded
        print(f"    [ok] eggs={len(raw_eggs)}", flush=True)
    else:
        session = _build_session()
        print("\n[>>] 拉取 egg/list（分页）", flush=True)
        raw_eggs = fetch_egg_list(session)
        print(f"    [ok] eggs={len(raw_eggs)}", flush=True)
        if args.cache_list:
            cache_path = Path(args.cache_list).expanduser().resolve()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps(raw_eggs, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"    [cache] 写入 {cache_path}", flush=True)

    rows, parse_warnings = _normalize_eggs(raw_eggs)
    if not rows:
        print("[error] 未解析到有效 egg 数据，终止。", flush=True)
        sys.exit(1)

    conn = _pg_conn()
    conn.autocommit = False
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)

            print("\n[>>] 反查 pokemon.id（按 source_id 匹配 related_pet_id）", flush=True)
            resolve_notes = _resolve_pokemon_ids(cur, rows)
            matched = sum(1 for r in rows if r["pokemon_id"] is not None)
            unlinked = len(rows) - matched
            print(
                f"    [ok] matched={matched}/{len(rows)} "
                f"unlinked={unlinked} (no_related={len(resolve_notes['no_related'])}, "
                f"not_found={len(resolve_notes['not_found'])})",
                flush=True,
            )

            cur.executemany(
                """
                INSERT INTO pokemon_egg (
                    source_id, name, form, icon,
                    pokemon_source_id, pokemon_id, item_quality
                ) VALUES (
                    %(source_id)s, %(name)s, %(form)s, %(icon)s,
                    %(pokemon_source_id)s, %(pokemon_id)s, %(item_quality)s
                )
                ON CONFLICT (source_id) DO UPDATE SET
                    name              = EXCLUDED.name,
                    form              = EXCLUDED.form,
                    icon              = EXCLUDED.icon,
                    pokemon_source_id = EXCLUDED.pokemon_source_id,
                    pokemon_id        = EXCLUDED.pokemon_id,
                    item_quality      = EXCLUDED.item_quality,
                    updated_at        = NOW()
                """,
                rows,
            )

        if args.dry_run:
            conn.rollback()
            print(
                f"\n[dry-run] 已回滚，未写入 PostgreSQL（预计 upsert {len(rows)} 条，其中 {unlinked} 条无 pokemon_id 关联）",
                flush=True,
            )
        else:
            conn.commit()
            print(
                f"\n[commit] 已写入/更新 {len(rows)} 条 pokemon_egg 记录（其中 {unlinked} 条无 pokemon_id 关联）",
                flush=True,
            )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    for warning in parse_warnings:
        print(warning, file=sys.stderr)

    def _print_notes(title: str, items: list[str], limit: int = 30) -> None:
        if not items:
            return
        print(f"\n[info] {title}: {len(items)} 条", flush=True)
        for item in items[:limit]:
            print(f"  - {item}", flush=True)
        if len(items) > limit:
            print(f"  ... 还有 {len(items) - limit} 条已省略", flush=True)

    _print_notes("无 related_pet_id（已落库，pokemon_id=NULL）", resolve_notes["no_related"])
    _print_notes("related_pet_id 在 pokemon.source_id 中查无（已落库，pokemon_id=NULL）", resolve_notes["not_found"])
    _print_notes("related_pet_id 命中多个 pokemon（取第一个）", resolve_notes["ambiguous"])

    print(f"\n[summary] elapsed={time.time() - total_start:.2f}s", flush=True)


if __name__ == "__main__":
    main()
