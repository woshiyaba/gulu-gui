"""
从官方 base_info 接口拉取宠物描述（desc），写入 pokemon.desc。

数据流：
  pokemon.source_id → https://rocom.qq.com/.../base_info/{source_id}.json
  接口 JSON.desc → 写入 pokemon.desc
  若指定 --update true，则同时把接口的种族值写入 pokemon 的种族值字段：
      hp        → hp
      adAttack  → atk      (物攻)
      apAttack  → matk     (魔攻)
      adDefense → def_val  (物防)
      apDefense → mdef     (魔防)
      speed     → spd
      合计       → total_race

不传 --update（或 --update false）时只插入/更新 desc 字段。
传 --mode insert 时，按指定 source_id 或小黑盒宠物列表中的全部 source_id
拉取 base_info，并把不存在的宠物插入 pokemon。

用法：
    uv run python scripts/import_pokemon_desc.py
    uv run python scripts/import_pokemon_desc.py --update true
    uv run python scripts/import_pokemon_desc.py --mode insert --only-ids 3010,3004
    uv run python scripts/import_pokemon_desc.py --mode insert --dry-run
    uv run python scripts/import_pokemon_desc.py --dry-run
    uv run python scripts/import_pokemon_desc.py --only-ids 3010,3004
    uv run python scripts/import_pokemon_desc.py --sleep 0.5
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras
import requests

from config import PG_CONFIG


BASE_INFO_URL = "https://rocom.qq.com/cp/rocom_game_manager_json/prod/sprite/base_info/{source_id}.json"

COMMON_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
}


def _ensure_utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def _step(message: str) -> float:
    print(f"\n[>>] {message} ...", flush=True)
    return time.time()


def _done(message: str) -> None:
    print(f"    [ok] {message}", flush=True)


def _warn_list(title: str, items: list[str], limit: int = 30) -> None:
    if not items:
        return
    print(f"\n[warn] {title}: {len(items)} 条", flush=True)
    for item in items[:limit]:
        print(f"  - {item}", flush=True)
    if len(items) > limit:
        print(f"  ... 还有 {len(items) - limit} 条，已省略", flush=True)


def _to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _clean_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(**PG_CONFIG)


def parse_ids(value: str) -> set[int]:
    ids: set[int] = set()
    for chunk in value.replace("，", ",").replace(",", "\n").splitlines():
        token = chunk.strip()
        if token:
            ids.add(int(token))
    return ids


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(COMMON_HEADERS)
    return session


def fetch_base_info(session: requests.Session, source_id: int) -> dict[str, Any] | None:
    url = BASE_INFO_URL.format(source_id=source_id)
    resp = session.get(url, timeout=20)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        return None
    return data


def load_pokemon_rows(cur, only_ids: set[int]) -> list[dict[str, Any]]:
    """加载需要处理的 pokemon（id, source_id），仅取 source_id 非空者。"""
    if only_ids:
        cur.execute(
            """
            SELECT id, name, source_id
              FROM pokemon
             WHERE source_id IS NOT NULL
               AND source_id = ANY(%s)
             ORDER BY id
            """,
            (list(only_ids),),
        )
    else:
        cur.execute(
            """
            SELECT id, name, source_id
              FROM pokemon
             WHERE source_id IS NOT NULL
             ORDER BY id
            """
        )
    return list(cur.fetchall())


def load_insert_source_rows(
    only_ids: set[int], max_pets: int | None
) -> list[dict[str, Any]]:
    """加载 insert 模式的 source_id 列表。"""
    if only_ids:
        return [{"source_id": source_id} for source_id in sorted(only_ids)]

    from scripts.sync_xiaoheihe_pets import (
        _build_session as build_xiaoheihe_session,
        fetch_pet_list,
    )

    pets = fetch_pet_list(build_xiaoheihe_session(), max_pets=max_pets)
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for pet in pets:
        source_id = _to_int(pet.get("id"))
        if source_id <= 0 or source_id in seen:
            continue
        seen.add(source_id)
        rows.append(
            {
                "source_id": source_id,
                "name": _clean_str(pet.get("name")),
                "avatar": _clean_str(pet.get("icon")),
                "form_name": _clean_str(pet.get("form")),
                "no": _to_int(pet.get("pictorial_book_id")),
            }
        )
    return rows


def build_race_values(info: dict[str, Any]) -> dict[str, int]:
    hp = _to_int(info.get("hp"))
    atk = _to_int(info.get("adAttack"))
    matk = _to_int(info.get("apAttack"))
    def_val = _to_int(info.get("adDefense"))
    mdef = _to_int(info.get("apDefense"))
    spd = _to_int(info.get("speed"))
    return {
        "hp": hp,
        "atk": atk,
        "matk": matk,
        "def_val": def_val,
        "mdef": mdef,
        "spd": spd,
        "total_race": hp + atk + matk + def_val + mdef + spd,
    }


def pokemon_exists_by_source_id(cur, source_id: int) -> int | None:
    cur.execute("SELECT id FROM pokemon WHERE source_id = %s LIMIT 1", (source_id,))
    row = cur.fetchone()
    return int(row["id"]) if row else None


def upsert_feature_trait(cur, info: dict[str, Any]) -> int:
    feature = _clean_str(info.get("feature"))
    name = f"特性{feature}" if feature else "未知特性"
    desc = _clean_str(info.get("featureDesc"))
    cur.execute(
        """
        INSERT INTO pokemon_trait (name, description)
        VALUES (%s, %s)
        ON CONFLICT (name) DO UPDATE
          SET description = CASE
                WHEN EXCLUDED.description <> '' THEN EXCLUDED.description
                ELSE pokemon_trait.description
              END
        RETURNING id
        """,
        (name, desc),
    )
    return int(cur.fetchone()["id"])


def insert_pokemon_from_base_info(
    cur,
    source_id: int,
    info: dict[str, Any],
    hint: dict[str, Any],
) -> int | None:
    name = _clean_str(info.get("name")) or _clean_str(hint.get("name"))
    if not name:
        return None

    race = build_race_values(info)
    trait_id = upsert_feature_trait(cur, info)
    no_value = _to_int(hint.get("no")) or _to_int(info.get("id")) or source_id
    desc = _clean_str(info.get("desc"))
    obtain_method = _clean_str(info.get("launchType")) or _clean_str(info.get("publicAt"))

    cur.execute(
        """
        INSERT INTO pokemon (
            no, name, avatar, form_name, trait_id,
            hp, atk, matk, def_val, mdef, spd, total_race,
            obtain_method, source_id, "desc"
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            f"NO.{no_value}",
            name,
            _clean_str(hint.get("avatar")),
            _clean_str(hint.get("form_name")),
            trait_id,
            race["hp"],
            race["atk"],
            race["matk"],
            race["def_val"],
            race["mdef"],
            race["spd"],
            race["total_race"],
            obtain_method,
            source_id,
            desc,
        ),
    )
    return int(cur.fetchone()["id"])


def main() -> None:
    _ensure_utf8_stdout()

    parser = argparse.ArgumentParser(description="拉取官方 base_info 写入 pokemon.desc")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正写库")
    parser.add_argument(
        "--mode",
        choices=("update", "insert"),
        default="update",
        help="update=更新已有 pokemon；insert=插入不存在的 source_id",
    )
    parser.add_argument(
        "--update",
        nargs="?",
        const="true",
        default="false",
        help="是否同时更新种族值（hp/atk/matk/def_val/mdef/spd/total_race），选填，默认 false 只写 desc",
    )
    parser.add_argument(
        "--only-ids",
        type=str,
        default=None,
        help="只处理指定 source_id，多个用逗号分隔",
    )
    parser.add_argument("--sleep", type=float, default=0.3, help="每次请求间的休眠秒数")
    parser.add_argument(
        "--max-pets",
        type=int,
        default=None,
        help="insert 全部时最多从小黑盒列表读取多少只宠物（联调用）",
    )
    args = parser.parse_args()

    mode = args.mode
    update_race = _to_bool(args.update)
    only_ids = parse_ids(args.only_ids) if args.only_ids else set()

    total_start = time.time()
    print("=" * 60)
    print("  拉取官方 base_info → pokemon.desc")
    print(
        f"  mode={mode} dry_run={args.dry_run} update_race={update_race} "
        f"only_ids={len(only_ids) or '全部'} max_pets={args.max_pets or '不限'}"
    )
    print("=" * 60)

    session = _build_session()
    conn = pg_conn()
    conn.autocommit = False

    stats = {
        "total": 0,
        "fetched": 0,
        "desc_updated": 0,
        "race_updated": 0,
        "inserted": 0,
        "skipped_existing": 0,
        "skipped_empty_name": 0,
        "not_found": 0,
        "fetch_failed": 0,
        "empty_desc": 0,
    }
    warnings: dict[str, list[str]] = {
        "not_found": [],
        "fetch_failed": [],
        "empty_desc": [],
        "skipped_existing": [],
        "skipped_empty_name": [],
    }

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if mode == "insert":
            t = _step("加载待插入 source_id")
            rows = load_insert_source_rows(only_ids, args.max_pets)
        else:
            t = _step("加载待处理 pokemon（source_id 非空）")
            rows = load_pokemon_rows(cur, only_ids)
        stats["total"] = len(rows)
        _done(f"待处理 {len(rows)} 条 ({time.time() - t:.2f}s)")

        if not rows:
            print("[error] 没有可处理的数据，终止。", flush=True)
            conn.rollback()
            sys.exit(1)

        _step("逐条拉取并写库")
        total = len(rows)
        for idx, row in enumerate(rows, start=1):
            source_id = int(row["source_id"])
            pokemon_id = int(row["id"]) if mode == "update" else 0
            name = row.get("name") or ""

            try:
                info = fetch_base_info(session, source_id)
            except Exception as exc:
                stats["fetch_failed"] += 1
                warnings["fetch_failed"].append(
                    f"id={pokemon_id or '-'} source_id={source_id} {name} err={exc}"
                )
                time.sleep(args.sleep)
                continue

            if info is None:
                stats["not_found"] += 1
                warnings["not_found"].append(
                    f"id={pokemon_id or '-'} source_id={source_id} {name}"
                )
                time.sleep(args.sleep)
                continue

            stats["fetched"] += 1
            desc = _clean_str(info.get("desc"))
            if not desc:
                stats["empty_desc"] += 1
                warnings["empty_desc"].append(
                    f"id={pokemon_id or '-'} source_id={source_id} {name}"
                )

            if mode == "insert":
                existing_id = pokemon_exists_by_source_id(cur, source_id)
                if existing_id is not None:
                    stats["skipped_existing"] += 1
                    warnings["skipped_existing"].append(
                        f"id={existing_id} source_id={source_id} {name}"
                    )
                    print(
                        f"    [{idx}/{total}] source_id={source_id} {name} 已存在 id={existing_id}，跳过",
                        flush=True,
                    )
                    time.sleep(args.sleep)
                    continue

                inserted_id = insert_pokemon_from_base_info(cur, source_id, info, row)
                if inserted_id is None:
                    stats["skipped_empty_name"] += 1
                    warnings["skipped_empty_name"].append(f"source_id={source_id}")
                    time.sleep(args.sleep)
                    continue

                stats["inserted"] += 1
                print(
                    f"    [{idx}/{total}] inserted id={inserted_id} source_id={source_id} "
                    f"{_clean_str(info.get('name')) or name} desc_len={len(desc)}",
                    flush=True,
                )
            elif update_race:
                race = build_race_values(info)
                cur.execute(
                    """
                    UPDATE pokemon
                       SET "desc"     = %s,
                           hp         = %s,
                           atk        = %s,
                           matk       = %s,
                           def_val    = %s,
                           mdef       = %s,
                           spd        = %s,
                           total_race = %s
                     WHERE id = %s
                    """,
                    (
                        desc,
                        race["hp"],
                        race["atk"],
                        race["matk"],
                        race["def_val"],
                        race["mdef"],
                        race["spd"],
                        race["total_race"],
                        pokemon_id,
                    ),
                )
                stats["race_updated"] += 1
                stats["desc_updated"] += 1
                print(
                    f"    [{idx}/{total}] id={pokemon_id} source_id={source_id} {name} "
                    f"desc_len={len(desc)} +race",
                    flush=True,
                )
            else:
                cur.execute(
                    'UPDATE pokemon SET "desc" = %s WHERE id = %s',
                    (desc, pokemon_id),
                )
                stats["desc_updated"] += 1
                print(
                    f"    [{idx}/{total}] id={pokemon_id} source_id={source_id} {name} "
                    f"desc_len={len(desc)}",
                    flush=True,
                )

            time.sleep(args.sleep)

        if args.dry_run:
            conn.rollback()
            print("\n[dry-run] 已回滚，未写入 PostgreSQL", flush=True)
        else:
            conn.commit()
            print("\n[commit] 已提交到 PostgreSQL", flush=True)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    _warn_list("接口 404 未找到（已跳过）", warnings["not_found"])
    _warn_list("接口请求失败（已跳过）", warnings["fetch_failed"])
    _warn_list("desc 为空（仍已写入空串）", warnings["empty_desc"])
    _warn_list("source_id 已存在（insert 模式已跳过）", warnings["skipped_existing"])
    _warn_list("name 为空（insert 模式已跳过）", warnings["skipped_empty_name"])

    print(
        f"\n[summary] total={stats['total']} fetched={stats['fetched']} "
        f"desc_updated={stats['desc_updated']} race_updated={stats['race_updated']} "
        f"inserted={stats['inserted']} skipped_existing={stats['skipped_existing']} "
        f"skipped_empty_name={stats['skipped_empty_name']} "
        f"not_found={stats['not_found']} fetch_failed={stats['fetch_failed']} "
        f"empty_desc={stats['empty_desc']} elapsed={time.time() - total_start:.2f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
