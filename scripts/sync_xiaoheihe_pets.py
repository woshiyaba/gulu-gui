"""
从小黑盒（xiaoheihe）API 同步精灵基础信息与技能到 PostgreSQL。

数据流：
  pet/list  → 按 name（form）匹配 pokemon → 更新 pokemon.source_id / pokemon.avatar
  pet/detail → 取 skill_list.level/blood/machine → 按 name 匹配 skill → 写入 pokemon_skill
  匹配不到的技能：先落库到 skill 表（attr_id=NULL），再写入 pokemon_skill，并打印日志。

匹配规则：
- pets.json[*].form 非空时，使用 `name（form）` 全角括号去匹配 pokemon.name
- form 为空时，直接使用 name 匹配

用法：
    uv run python scripts/sync_xiaoheihe_pets.py
    uv run python scripts/sync_xiaoheihe_pets.py --dry-run
    uv run python scripts/sync_xiaoheihe_pets.py --skip-detail
    uv run python scripts/sync_xiaoheihe_pets.py --max-pets 10
    uv run python scripts/sync_xiaoheihe_pets.py --only-ids-file docs/xiaoheihe/single_todo.txt
    uv run python scripts/sync_xiaoheihe_pets.py --skill-only-ids 3225,3226,3454,3455,3456
    uv run python scripts/sync_xiaoheihe_pets.py --skill-only-ids 3225,3226 --replace-blood-skills
    uv run python scripts/sync_xiaoheihe_pets.py --skill-only-ids 3225,3226 --replace-blood-skills all
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


LIST_URL = "https://api.xiaoheihe.cn/game/roco_kingdom/pet/list"
DETAIL_URL = "https://api.xiaoheihe.cn/game/roco_kingdom/pet/detail"
PAGE_SIZE = 20
NATIVE_SKILL_TYPE = "原生技能"
BLOOD_SKILL_TYPE = "血脉技能"
MACHINE_SKILL_TYPE = "技能石技能"
FUZZY_MATCH_MODE = "name_fuzzy"

# 同一只精灵同一技能只能保存一条关联，优先保留更具体的来源。
SKILL_SYNC_SOURCES = (
    ("blood", BLOOD_SKILL_TYPE),
    ("level", NATIVE_SKILL_TYPE),
    ("machine", MACHINE_SKILL_TYPE),
)
REPLACE_SKILL_TYPES_BY_MODE = {
    "blood": [BLOOD_SKILL_TYPE],
    "all": [NATIVE_SKILL_TYPE, BLOOD_SKILL_TYPE, MACHINE_SKILL_TYPE],
}

LIST_QUERY = {
    "app": "heybox",
    "heybox_id": "90642164",
    "os_type": "web",
    "x_app": "heybox",
    "x_client_type": "web",
    "x_os_type": "iOS",
    "x_client_version": "1.3.386",
    "version": "999.0.4",
    "hkey": "7TY0D94",
    "_time": "1777607783",
    "nonce": "09BC9AE8AAE114CEF58E32B9A88FBE8D",
}

DETAIL_QUERY = {
    "app": "heybox",
    "heybox_id": "90642164",
    "os_type": "web",
    "x_app": "heybox",
    "x_client_type": "web",
    "x_os_type": "iOS",
    "x_client_version": "1.3.386",
    "version": "999.0.4",
    "hkey": "TU2SY18",
    "_time": "1777607876",
    "nonce": "F97001435E948742E80B8DAE2A10ADAC",
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
    "x_xhh_tokenid=BEeRPQ4eUCIJkbsOEwF9hUtGWhuuMfF3I2jXmwc9kcnl4q+DfEeVyO/bzhOLGT20A34m3d/8l9vjB3cGRTQHadw==;"
    " user_heybox_id=90642164;"
    " user_pkey=MTc2MzUzMjQxNi40N185MDY0MjE2NHZjeWVpc3hzaHdqY2lxaWw__;"
    " x_heybox_id=90642164;"
    " x_pkey=MTc2MzUzMjQxNi40N185MDY0MjE2NHZjeWVpc3hzaHdqY2lxaWw__"
)


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


def _clean_str(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(COMMON_HEADERS)
    session.headers["Cookie"] = COOKIE_HEADER
    return session


def fetch_pet_list(session: requests.Session, *, max_pets: int | None) -> list[dict[str, Any]]:
    pets: list[dict[str, Any]] = []
    offset = 0
    while True:
        body = {
            "q": "",
            "filter_elems": "",
            "filter_shiny": "",
            "filter_stage": "",
            "offset": str(offset),
            "limit": str(PAGE_SIZE),
        }
        print(body)
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
            raise RuntimeError(f"pet/list 返回异常: {payload}")
        chunk = (payload.get("result") or {}).get("list") or []
        pets.extend(chunk)
        print(
            f"    [list] offset={offset} got={len(chunk)} total={len(pets)}",
            flush=True,
        )
        if len(chunk) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if max_pets is not None and len(pets) >= max_pets:
            break
        time.sleep(0.2)
    if max_pets is not None:
        pets = pets[:max_pets]
    return pets


def fetch_pet_detail(session: requests.Session, pet_id: str) -> dict[str, Any] | None:
    params = dict(DETAIL_QUERY)
    params["id"] = str(pet_id)
    resp = session.get(DETAIL_URL, params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "ok":
        print(f"    [warn] pet/detail id={pet_id} 状态异常: {payload.get('msg')}", flush=True)
        return None
    return (payload.get("result") or {}).get("pet_detail")


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(**PG_CONFIG)


def build_pokemon_match_key(name: str, form: str) -> str:
    name = _clean_str(name)
    form = _clean_str(form)
    if form:
        return f"{name}（{form}）"
    return name


def load_pet_ids(path: str) -> set[str]:
    ids_path = Path(path).expanduser().resolve()
    ids: set[str] = set()
    for line in ids_path.read_text(encoding="utf-8").splitlines():
        value = line.split("#", 1)[0].strip()
        if value:
            ids.add(value)
    return ids


def parse_pet_ids(value: str) -> set[str]:
    ids: set[str] = set()
    for chunk in value.replace("，", ",").replace(",", "\n").splitlines():
        pet_id = chunk.strip()
        if pet_id:
            ids.add(pet_id)
    return ids


def resolve_replace_skill_types(mode: str | None) -> list[str]:
    if not mode:
        return []
    return REPLACE_SKILL_TYPES_BY_MODE[mode]


def filter_pets_by_ids(
    pets: list[dict[str, Any]], pet_ids: set[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    filtered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pet in pets:
        pet_id = _clean_str(pet.get("id"))
        if pet_id in pet_ids:
            filtered.append(pet)
            seen.add(pet_id)
    missing_ids = sorted(
        pet_ids - seen,
        key=lambda item: int(item) if item.isdigit() else item,
    )
    return filtered, missing_ids


def _load_pokemon_index(cur) -> dict[str, list[int]]:
    cur.execute("SELECT id, name FROM pokemon")
    index: dict[str, list[int]] = {}
    for row in cur.fetchall():
        name = _clean_str(row["name"])
        if not name:
            continue
        index.setdefault(name, []).append(int(row["id"]))
    return index


def _find_pokemon_by_name_fuzzy(cur, name: str) -> list[dict[str, Any]]:
    name = _clean_str(name)
    if not name:
        return []
    pattern = f"%{_escape_like(name)}%"
    cur.execute(
        """
        SELECT id, name
          FROM pokemon
         WHERE name ILIKE %s ESCAPE '\\'
         ORDER BY
           CASE WHEN name = %s THEN 0 ELSE 1 END,
           CHAR_LENGTH(name),
           id
        """,
        (pattern, name),
    )
    return list(cur.fetchall())


def _resolve_fuzzy_candidates(rows: list[dict[str, Any]], pet_name: str) -> list[int]:
    """模糊命中多条时，只在唯一精确同名存在时自动收敛，避免误更新相近名字。"""
    if len(rows) <= 1:
        return [int(row["id"]) for row in rows]

    exact_rows = [row for row in rows if _clean_str(row["name"]) == pet_name]
    if len(exact_rows) == 1:
        return [int(exact_rows[0]["id"])]
    return [int(row["id"]) for row in rows]


def _format_candidate_rows(rows: list[dict[str, Any]]) -> str:
    return ",".join(f"{row['id']}:{row['name']}" for row in rows)


def _find_pokemon_candidates(
    cur,
    pokemon_index: dict[str, list[int]],
    pet: dict[str, Any],
    fuzzy_pet_ids: set[str],
    *,
    keep_all_fuzzy_matches: bool = False,
) -> tuple[list[int], str, str]:
    pet_id = _clean_str(pet.get("id"))
    if pet_id in fuzzy_pet_ids:
        pet_name = _clean_str(pet.get("name"))
        rows = _find_pokemon_by_name_fuzzy(cur, pet_name)
        if keep_all_fuzzy_matches:
            candidates = [int(row["id"]) for row in rows]
        else:
            candidates = _resolve_fuzzy_candidates(rows, pet_name)
        return candidates, f"name~{pet_name!r}", _format_candidate_rows(rows)

    match_key = build_pokemon_match_key(pet.get("name"), pet.get("form"))
    candidates = pokemon_index.get(match_key) or []
    return candidates, f"match_key={match_key!r}", ",".join(map(str, candidates))


def _load_skill_index(cur) -> dict[str, list[int]]:
    cur.execute("SELECT id, name FROM skill")
    index: dict[str, list[int]] = {}
    for row in cur.fetchall():
        name = _clean_str(row["name"])
        if not name:
            continue
        index.setdefault(name, []).append(int(row["id"]))
    return index


def _insert_missing_skill(cur, entry: dict[str, Any]) -> int:
    name = _clean_str(entry.get("name"))
    icon = _clean_str(entry.get("icon"))
    desc = _clean_str(entry.get("desc"))
    skill_type = _clean_str(entry.get("category"))
    consume = int(entry.get("cost") or 0)
    power = int(entry.get("power") or 0)

    cur.execute(
        """
        INSERT INTO skill (name, attr_id, power, type, consume, skill_desc, icon)
        VALUES (%s, NULL, %s, %s, %s, %s, %s)
        ON CONFLICT (name) DO UPDATE
          SET power      = EXCLUDED.power,
              type       = EXCLUDED.type,
              consume    = EXCLUDED.consume,
              skill_desc = EXCLUDED.skill_desc,
              icon       = EXCLUDED.icon
        RETURNING id
        """,
        (name, power, skill_type, consume, desc, icon),
    )
    return int(cur.fetchone()["id"])


def _delete_existing_skills(
    cur, pokemon_ids: list[int], skill_source_types: list[str]
) -> int:
    if not pokemon_ids or not skill_source_types:
        return 0

    cur.execute(
        """
        DELETE FROM pokemon_skill
         WHERE pokemon_id = ANY(%s)
           AND type = ANY(%s)
        """,
        (pokemon_ids, skill_source_types),
    )
    return int(cur.rowcount or 0)


def update_pokemon_source(
    cur, pets: list[dict[str, Any]], *, fuzzy_pet_ids: set[str] | None = None
) -> tuple[int, list[str], list[str]]:
    """根据 pets 更新 pokemon.source_id / pokemon.avatar，返回 (source_id → pokemon_id) 映射所需信息。"""
    pokemon_index = _load_pokemon_index(cur)
    fuzzy_pet_ids = fuzzy_pet_ids or set()

    updated = 0
    missing: list[str] = []
    ambiguous: list[str] = []

    for pet in pets:
        pet_id = _clean_str(pet.get("id"))
        if not pet_id:
            continue
        candidates, match_desc, hits_desc = _find_pokemon_candidates(
            cur, pokemon_index, pet, fuzzy_pet_ids
        )
        if not candidates:
            missing.append(f"pet_id={pet_id} {match_desc}")
            continue
        if len(candidates) > 1:
            ambiguous.append(
                f"pet_id={pet_id} {match_desc} hits=[{hits_desc}]"
            )
            continue
        pokemon_id = candidates[0]
        cur.execute(
            """
            UPDATE pokemon
               SET source_id = %s,
                   avatar    = %s
             WHERE id = %s
            """,
            (int(pet_id), _clean_str(pet.get("icon")), pokemon_id),
        )
        updated += 1

    return updated, missing, ambiguous


def sync_pet_skills(
    cur,
    session: requests.Session,
    pets: list[dict[str, Any]],
    *,
    sleep_seconds: float,
    fuzzy_pet_ids: set[str] | None = None,
    allow_multi_pokemon: bool = False,
    replace_skill_types: list[str] | None = None,
) -> dict[str, Any]:
    """对每个 pet 拉取详情，处理 skill_list 三类技能，写入 pokemon_skill。"""
    pokemon_index = _load_pokemon_index(cur)
    skill_index = _load_skill_index(cur)
    fuzzy_pet_ids = fuzzy_pet_ids or set()
    replace_skill_types = replace_skill_types or []

    stats = {
        "processed": 0,
        "skipped_no_pokemon": 0,
        "skipped_detail_failed": 0,
        "skill_total": 0,
        "skill_matched": 0,
        "skill_inserted": 0,
        "level_total": 0,
        "blood_total": 0,
        "machine_total": 0,
        "pokemon_skill_deleted": 0,
        "pokemon_skill_inserted": 0,
        "pokemon_skill_existing": 0,
    }
    warnings: dict[str, list[str]] = {
        "missing_skill_inserted": [],
        "ambiguous_pokemon": [],
        "ambiguous_skill": [],
        "duplicate_skill_source": [],
        "detail_failed": [],
        "invalid_skill_section": [],
        "no_skill_section": [],
    }

    total = len(pets)
    for idx, pet in enumerate(pets, start=1):
        pet_id = _clean_str(pet.get("id"))
        match_key = build_pokemon_match_key(pet.get("name"), pet.get("form"))
        candidates, match_desc, hits_desc = _find_pokemon_candidates(
            cur,
            pokemon_index,
            pet,
            fuzzy_pet_ids,
            keep_all_fuzzy_matches=allow_multi_pokemon,
        )
        if not candidates or (len(candidates) > 1 and not allow_multi_pokemon):
            stats["skipped_no_pokemon"] += 1
            if len(candidates) > 1:
                warnings["ambiguous_pokemon"].append(
                    f"pet_id={pet_id} {match_desc} hits=[{hits_desc}]"
                )
            continue
        pokemon_ids = candidates
        stats["processed"] += len(pokemon_ids)

        print(
            f"    [{idx}/{total}] detail id={pet_id} pokemon_ids={pokemon_ids} {match_key}",
            flush=True,
        )
        try:
            detail = fetch_pet_detail(session, pet_id)
        except Exception as exc:
            stats["skipped_detail_failed"] += 1
            warnings["detail_failed"].append(f"pet_id={pet_id} {match_key} err={exc}")
            time.sleep(sleep_seconds)
            continue

        if not detail:
            stats["skipped_detail_failed"] += 1
            warnings["detail_failed"].append(f"pet_id={pet_id} {match_key} 详情为空")
            time.sleep(sleep_seconds)
            continue

        skill_list = detail.get("skill_list") or {}
        if not isinstance(skill_list, dict):
            warnings["invalid_skill_section"].append(f"pet_id={pet_id} {match_key} skill_list 不是对象")
            time.sleep(sleep_seconds)
            continue

        if replace_skill_types:
            stats["pokemon_skill_deleted"] += _delete_existing_skills(
                cur, pokemon_ids, replace_skill_types
            )

        has_any_skill = False
        planned_skill_ids: set[int] = set()
        for source_key, source_type in SKILL_SYNC_SOURCES:
            entries = skill_list.get(source_key) or []
            if not entries:
                continue
            if not isinstance(entries, list):
                warnings["invalid_skill_section"].append(
                    f"pet_id={pet_id} {match_key} skill_list.{source_key} 不是数组"
                )
                continue

            has_any_skill = True
            for sort_order, entry in enumerate(entries, start=1):
                if not isinstance(entry, dict):
                    warnings["invalid_skill_section"].append(
                        f"pet_id={pet_id} {match_key} skill_list.{source_key}[{sort_order}] 不是对象"
                    )
                    continue

                skill_name = _clean_str(entry.get("name"))
                if not skill_name:
                    continue
                stats["skill_total"] += 1
                stats[f"{source_key}_total"] += 1

                matched = skill_index.get(skill_name) or []
                if len(matched) > 1:
                    warnings["ambiguous_skill"].append(
                        f"pet_id={pet_id} skill={skill_name!r} skill_ids=[{','.join(map(str, matched))}]"
                    )
                    continue

                if matched:
                    skill_id = matched[0]
                    matched_existing_skill = True
                else:
                    skill_id = _insert_missing_skill(cur, entry)
                    skill_index[skill_name] = [skill_id]
                    matched_existing_skill = False
                    warnings["missing_skill_inserted"].append(
                        f"pet_id={pet_id} pokemon_ids={pokemon_ids} "
                        f"source={source_key} skill={skill_name!r} new_skill_id={skill_id}"
                    )

                if skill_id in planned_skill_ids:
                    warnings["duplicate_skill_source"].append(
                        f"pet_id={pet_id} skill={skill_name!r} source={source_key} "
                        "已在更高优先级技能来源中写入"
                    )
                    continue

                if matched_existing_skill:
                    stats["skill_matched"] += 1
                else:
                    stats["skill_inserted"] += 1
                planned_skill_ids.add(skill_id)

                for pokemon_id in pokemon_ids:
                    cur.execute(
                        """
                        INSERT INTO pokemon_skill (pokemon_id, skill_id, type, sort_order)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (pokemon_id, skill_id) DO UPDATE
                          SET type       = EXCLUDED.type,
                              sort_order = EXCLUDED.sort_order
                        RETURNING xmax
                        """,
                        (pokemon_id, skill_id, source_type, sort_order),
                    )
                    row = cur.fetchone()
                    if row and int(row["xmax"]) == 0:
                        stats["pokemon_skill_inserted"] += 1
                    else:
                        stats["pokemon_skill_existing"] += 1

        if not has_any_skill:
            warnings["no_skill_section"].append(f"pet_id={pet_id} {match_key}")

        time.sleep(sleep_seconds)

    return {"stats": stats, "warnings": warnings}


def main() -> None:
    _ensure_utf8_stdout()

    parser = argparse.ArgumentParser(description="同步 xiaoheihe pet 数据到 PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正写库")
    parser.add_argument("--skip-detail", action="store_true", help="只同步 source_id/avatar，跳过技能")
    parser.add_argument("--max-pets", type=int, default=None, help="最多处理多少只精灵（用于联调）")
    parser.add_argument("--sleep", type=float, default=0.3, help="每次详情请求间的休眠秒数")
    parser.add_argument(
        "--cache-list",
        type=str,
        default=None,
        help="若指定，则把 pet/list 全量结果写入该 JSON 文件（用于排查）",
    )
    parser.add_argument(
        "--from-cache",
        type=str,
        default=None,
        help="若指定，则跳过 pet/list 调用，直接读取该 JSON 文件中的 pets 列表",
    )
    parser.add_argument(
        "--only-ids-file",
        type=str,
        default=None,
        help="只处理文件中的 xiaoheihe pet id，并对这些 id 使用 name 模糊匹配 pokemon",
    )
    parser.add_argument(
        "--skill-only-ids",
        type=str,
        default=None,
        help="只同步指定 xiaoheihe pet id 的技能，多个 id 用逗号分隔；模糊命中多条 pokemon 时全部写入",
    )
    parser.add_argument(
        "--replace-blood-skills",
        nargs="?",
        const="blood",
        choices=("blood", "all"),
        default=None,
        help="同步前先删旧关联再重写；不带值只删血脉技能，传 all 删除原生/血脉/技能石三类",
    )
    args = parser.parse_args()
    file_pet_ids = load_pet_ids(args.only_ids_file) if args.only_ids_file else set()
    skill_only_pet_ids = (
        parse_pet_ids(args.skill_only_ids) if args.skill_only_ids else set()
    )
    only_pet_ids = file_pet_ids | skill_only_pet_ids
    skill_only_mode = bool(skill_only_pet_ids)
    replace_skill_types = resolve_replace_skill_types(args.replace_blood_skills)

    total_start = time.time()
    print("=" * 60)
    print("  同步 xiaoheihe pet 数据 → PostgreSQL")
    print(
        f"  dry_run={args.dry_run} skip_detail={args.skip_detail} "
        f"replace_blood_skills={args.replace_blood_skills or '-'} max_pets={args.max_pets}"
    )
    if args.only_ids_file:
        print(
            f"  only_ids_file={args.only_ids_file} "
            f"ids={len(file_pet_ids)} match={FUZZY_MATCH_MODE}"
        )
    if args.skill_only_ids:
        print(
            f"  skill_only_ids={','.join(sorted(skill_only_pet_ids))} "
            f"match={FUZZY_MATCH_MODE} multi_pokemon=all"
        )
    print("=" * 60)

    if args.only_ids_file and not file_pet_ids:
        print("[error] --only-ids-file 未读取到任何 id，终止。", flush=True)
        sys.exit(1)
    if args.skill_only_ids and not skill_only_pet_ids:
        print("[error] --skill-only-ids 未读取到任何 id，终止。", flush=True)
        sys.exit(1)
    if skill_only_mode and args.skip_detail:
        print("[error] --skill-only-ids 需要同步详情，不能同时使用 --skip-detail。", flush=True)
        sys.exit(1)
    if args.replace_blood_skills and args.skip_detail:
        print("[error] --replace-blood-skills 需要同步详情，不能同时使用 --skip-detail。", flush=True)
        sys.exit(1)

    session = _build_session()

    if args.from_cache:
        cache_path = Path(args.from_cache).expanduser().resolve()
        t = _step(f"加载 pets 缓存: {cache_path}")
        pets = json.loads(cache_path.read_text(encoding="utf-8"))
        if isinstance(pets, dict):
            pets = ((pets.get("result") or {}).get("list")) or []
        if args.max_pets is not None:
            pets = pets[: args.max_pets]
        _done(f"pets={len(pets)} ({time.time() - t:.2f}s)")
    else:
        t = _step("拉取 pet/list（分页）")
        pets = fetch_pet_list(session, max_pets=args.max_pets)
        _done(f"pets={len(pets)} ({time.time() - t:.2f}s)")
        if args.cache_list:
            cache_path = Path(args.cache_list).expanduser().resolve()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps(pets, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"    [cache] 写入 {cache_path}", flush=True)

    if only_pet_ids:
        t = _step("按 only ids 过滤 pet/list 结果")
        pets, missing_ids = filter_pets_by_ids(pets, only_pet_ids)
        _done(
            f"pets={len(pets)} missing_ids={len(missing_ids)} "
            f"({time.time() - t:.2f}s)"
        )
        _warn_list("pet/list 未包含的指定 id", missing_ids)

    if not pets:
        print("[error] 未取到任何精灵，终止。", flush=True)
        sys.exit(1)

    conn = pg_conn()
    conn.autocommit = False

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if skill_only_mode:
            print(
                "\n[skip] --skill-only-ids 已开启，跳过 pokemon.source_id / pokemon.avatar 更新",
                flush=True,
            )
        else:
            t = _step("匹配并更新 pokemon.source_id / pokemon.avatar")
            updated, missing, ambiguous = update_pokemon_source(
                cur, pets, fuzzy_pet_ids=only_pet_ids
            )
            _done(
                f"updated={updated} missing={len(missing)} ambiguous={len(ambiguous)} "
                f"({time.time() - t:.2f}s)"
            )
            _warn_list("未匹配到 pokemon 的 pet（已跳过）", missing)
            _warn_list("匹配到多个 pokemon 的 pet（已跳过）", ambiguous)

        if args.skip_detail:
            print("\n[skip] --skip-detail 已开启，跳过技能同步", flush=True)
            skill_result: dict[str, Any] | None = None
        else:
            t = _step("同步 pet/detail 三类技能 → pokemon_skill")
            skill_result = sync_pet_skills(
                cur,
                session,
                pets,
                sleep_seconds=args.sleep,
                fuzzy_pet_ids=only_pet_ids,
                allow_multi_pokemon=skill_only_mode,
                replace_skill_types=replace_skill_types,
            )
            stats = skill_result["stats"]
            _done(
                f"processed={stats['processed']} skills={stats['skill_total']} "
                f"level={stats['level_total']} blood={stats['blood_total']} machine={stats['machine_total']} "
                f"matched={stats['skill_matched']} inserted_skill={stats['skill_inserted']} "
                f"link_deleted={stats['pokemon_skill_deleted']} "
                f"link_inserted={stats['pokemon_skill_inserted']} link_updated={stats['pokemon_skill_existing']} "
                f"({time.time() - t:.2f}s)"
            )
            warnings = skill_result["warnings"]
            _warn_list("详情接口失败", warnings["detail_failed"])
            _warn_list("无 level/blood/machine 技能节点", warnings["no_skill_section"])
            _warn_list("无效技能节点", warnings["invalid_skill_section"])
            _warn_list(
                "精灵名命中多条 pokemon 记录（已跳过）",
                warnings["ambiguous_pokemon"],
            )
            _warn_list("技能名命中多条 skill 记录（已跳过）", warnings["ambiguous_skill"])
            _warn_list("同一技能出现在多个来源（已按优先级去重）", warnings["duplicate_skill_source"])
            _warn_list("未匹配到 skill 已新建并落库", warnings["missing_skill_inserted"])

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

    print(
        f"\n[summary] elapsed={time.time() - total_start:.2f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
