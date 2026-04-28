"""
从外部宠物 JSON 目录重建 pokemon_skill 到 PostgreSQL。

规则：
1. 用 JSON 根级 name 对应 pokemon.name_en，找到精灵 id。
2. 遍历 move_pool，用技能名匹配 skill.name，生成为「原生技能」。
3. 遍历 move_stones，用技能名匹配 skill.name，生成为「技能石技能」。
4. 对于成功匹配到唯一精灵的 JSON，不保留该精灵原先的 pokemon_skill，
   而是先删掉旧记录，再用 JSON 解析出的新技能全集重建。

说明：
- 仓库当前业务值统一是「技能石技能」；
  脚本按「技能石技能」写库，避免前后端枚举值不一致。
- 同一技能若同时出现在 move_pool 和 move_stones，优先按「原生技能」保留。

用法：
    uv run python scripts/sync_pokemon_skills_from_pet_jsons.py
    uv run python scripts/sync_pokemon_skills_from_pet_jsons.py --dry-run
    uv run python scripts/sync_pokemon_skills_from_pet_jsons.py --data-dir "E:/path/to/pets"
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

from config import PG_CONFIG

DEFAULT_DATA_DIR = Path(r"E:\game\洛克王国世界\plug\rocom.aoe.top-main\public\data\pets")
NATIVE_SKILL_TYPE = "原生技能"
LEARN_SKILL_TYPE = "技能石技能"
def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(**PG_CONFIG)


def _ensure_utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


def _step(message: str) -> float:
    print(f"\n[>>] {message} ...", flush=True)
    return time.time()


def _done(message: str) -> None:
    print(f"    [ok] {message}", flush=True)


def _warn_list(title: str, items: list[str], limit: int = 20) -> None:
    if not items:
        return
    print(f"\n[warn] {title}: {len(items)} 条", flush=True)
    for item in items[:limit]:
        print(f"  - {item}", flush=True)
    if len(items) > limit:
        print(f"  ... 还有 {len(items) - limit} 条，已省略", flush=True)


def _clean_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value else None


def _iter_json_files(data_dir: Path) -> list[Path]:
    def sort_key(path: Path) -> tuple[int, str]:
        stem = path.stem
        return (0, f"{int(stem):012d}") if stem.isdigit() else (1, stem.lower())

    return sorted((p for p in data_dir.glob("*.json") if p.is_file()), key=sort_key)


def _ensure_name_en_column(cur) -> None:
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'pokemon'
          AND column_name = 'name_en'
        """
    )
    if int(cur.fetchone()["cnt"]) == 0:
        raise SystemExit("[error] PostgreSQL 表 pokemon 缺少 name_en 字段，无法按 name_en 匹配精灵。")


def _load_pokemon_map(cur) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    cur.execute("SELECT id, name, name_en FROM pokemon ORDER BY id")
    pokemon_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    empty_name_en: list[str] = []

    for row in cur.fetchall():
        name_en = _clean_str(row.get("name_en"))
        if not name_en:
            empty_name_en.append(f"id={row['id']} name={row['name']!r}")
            continue
        pokemon_map[name_en].append(row)

    return dict(pokemon_map), empty_name_en


def _load_skill_map(cur) -> dict[str, list[dict[str, Any]]]:
    cur.execute("SELECT id, name FROM skill ORDER BY id")
    skill_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in cur.fetchall():
        skill_name = _clean_str(row.get("name"))
        if skill_name:
            skill_map[skill_name].append(row)
    return dict(skill_map)


def _count_existing_rows(cur, pokemon_ids: list[int]) -> int:
    if not pokemon_ids:
        return 0
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM pokemon_skill WHERE pokemon_id = ANY(%s)",
        (pokemon_ids,),
    )
    return int(cur.fetchone()["cnt"])


def _collect_replacement_links(
    *,
    entries: Any,
    source_label: str,
    pokemon_id: int,
    pokemon_name_en: str,
    file_path: Path,
    target_type: str,
    skill_map: dict[str, list[dict[str, Any]]],
    planned_skill_ids: set[int],
    stats: dict[str, int],
    warnings: dict[str, list[str]],
) -> list[tuple[int, int, str, int]]:
    if not isinstance(entries, list):
        stats["invalid_entries"] += 1
        warnings["invalid_entries"].append(
            f"{file_path.name} name_en={pokemon_name_en!r} {source_label} 不是数组"
        )
        return []

    values: list[tuple[int, int, str, int]] = []

    for sort_order, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            stats["invalid_entries"] += 1
            warnings["invalid_entries"].append(
                f"{file_path.name} name_en={pokemon_name_en!r} {source_label}[{sort_order}] 不是对象"
            )
            continue

        skill_name = _clean_str(entry.get("name"))
        if not skill_name:
            stats["invalid_entries"] += 1
            warnings["invalid_entries"].append(
                f"{file_path.name} name_en={pokemon_name_en!r} {source_label}[{sort_order}] 缺少 name"
            )
            continue

        matched_skills = skill_map.get(skill_name) or []
        if not matched_skills:
            stats["missing_skill"] += 1
            warnings["missing_skill"].append(
                f"{file_path.name} name_en={pokemon_name_en!r} skill={skill_name!r} source={source_label}"
            )
            continue

        if len(matched_skills) > 1:
            stats["ambiguous_skill"] += 1
            ids = ",".join(str(item["id"]) for item in matched_skills)
            warnings["ambiguous_skill"].append(
                f"{file_path.name} name_en={pokemon_name_en!r} skill={skill_name!r} ids=[{ids}]"
            )
            continue

        skill_id = int(matched_skills[0]["id"])
        if skill_id in planned_skill_ids:
            stats["duplicate_skill_in_json"] += 1
            warnings["duplicate_skill_in_json"].append(
                f"{file_path.name} name_en={pokemon_name_en!r} skill={skill_name!r} source={source_label} "
                f"已在同一 JSON 的更高优先级技能来源中出现"
            )
            continue

        values.append((pokemon_id, skill_id, target_type, sort_order))
        planned_skill_ids.add(skill_id)

    return values


def main() -> None:
    _ensure_utf8_stdout()

    parser = argparse.ArgumentParser(description="从宠物 JSON 目录重建 pokemon_skill 到 PostgreSQL")
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help=f"宠物 JSON 目录（默认: {DEFAULT_DATA_DIR}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印统计信息并回滚，不真正写库",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    if not data_dir.is_dir():
        print(f"[error] 目录不存在: {data_dir}")
        sys.exit(1)

    json_files = _iter_json_files(data_dir)
    if not json_files:
        print(f"[error] 目录下未找到 JSON 文件: {data_dir}")
        sys.exit(1)

    total_start = time.time()
    print("=" * 60)
    print("  同步宠物技能关联 → PostgreSQL")
    print(f"  data_dir: {data_dir}")
    print(f"  files: {len(json_files)}")
    print(f"  dry_run: {args.dry_run}")
    print("=" * 60)

    stats = {
        "files": 0,
        "invalid_json": 0,
        "invalid_entries": 0,
        "missing_name_en": 0,
        "missing_pokemon": 0,
        "ambiguous_pokemon": 0,
        "missing_skill": 0,
        "ambiguous_skill": 0,
        "duplicate_skill_in_json": 0,
        "duplicate_pokemon_json": 0,
        "replaced_pokemon": 0,
        "deleted_old_rows": 0,
        "inserted_rows": 0,
        "inserted_native": 0,
        "inserted_learn": 0,
    }
    warnings: dict[str, list[str]] = {
        "pokemon_without_name_en": [],
        "invalid_json": [],
        "invalid_entries": [],
        "missing_name_en": [],
        "missing_pokemon": [],
        "ambiguous_pokemon": [],
        "missing_skill": [],
        "ambiguous_skill": [],
        "duplicate_skill_in_json": [],
        "duplicate_pokemon_json": [],
    }

    conn = pg_conn()
    conn.autocommit = False

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        t = _step("加载 PostgreSQL 映射")
        _ensure_name_en_column(cur)
        pokemon_map, pokemon_without_name_en = _load_pokemon_map(cur)
        skill_map = _load_skill_map(cur)
        _done(
            f"pokemon(name_en)={len(pokemon_map)} skill={len(skill_map)} ({time.time() - t:.2f}s)"
        )

        warnings["pokemon_without_name_en"].extend(pokemon_without_name_en)

        replacement_by_pokemon: dict[int, list[tuple[int, int, str, int]]] = {}
        replacement_source_file: dict[int, str] = {}

        t = _step("扫描 JSON 文件")
        for file_path in json_files:
            stats["files"] += 1
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - 仅用于脚本运行时日志
                stats["invalid_json"] += 1
                warnings["invalid_json"].append(f"{file_path.name}: {exc}")
                continue

            if not isinstance(payload, dict):
                stats["invalid_json"] += 1
                warnings["invalid_json"].append(f"{file_path.name}: 根节点不是对象")
                continue

            pokemon_name_en = _clean_str(payload.get("name"))
            if not pokemon_name_en:
                stats["missing_name_en"] += 1
                warnings["missing_name_en"].append(f"{file_path.name}: JSON 根级缺少 name")
                continue

            matched_pokemons = pokemon_map.get(pokemon_name_en) or []
            if not matched_pokemons:
                stats["missing_pokemon"] += 1
                warnings["missing_pokemon"].append(
                    f"{file_path.name} name_en={pokemon_name_en!r} 在 pokemon 中未找到"
                )
                continue

            if len(matched_pokemons) > 1:
                stats["ambiguous_pokemon"] += 1
                ids = ",".join(str(item["id"]) for item in matched_pokemons)
                warnings["ambiguous_pokemon"].append(
                    f"{file_path.name} name_en={pokemon_name_en!r} 命中多个精灵 ids=[{ids}]"
                )
                continue

            pokemon_id = int(matched_pokemons[0]["id"])
            planned_skill_ids: set[int] = set()
            native_values = _collect_replacement_links(
                entries=payload.get("move_pool"),
                source_label="move_pool",
                pokemon_id=pokemon_id,
                pokemon_name_en=pokemon_name_en,
                file_path=file_path,
                target_type=NATIVE_SKILL_TYPE,
                skill_map=skill_map,
                planned_skill_ids=planned_skill_ids,
                stats=stats,
                warnings=warnings,
            )
            learn_values = _collect_replacement_links(
                entries=payload.get("move_stones"),
                source_label="move_stones",
                pokemon_id=pokemon_id,
                pokemon_name_en=pokemon_name_en,
                file_path=file_path,
                target_type=LEARN_SKILL_TYPE,
                skill_map=skill_map,
                planned_skill_ids=planned_skill_ids,
                stats=stats,
                warnings=warnings,
            )

            if pokemon_id in replacement_by_pokemon:
                prev_file = replacement_source_file[pokemon_id]
                stats["duplicate_pokemon_json"] += 1
                warnings["duplicate_pokemon_json"].append(
                    f"pokemon_id={pokemon_id} name_en={pokemon_name_en!r} "
                    f"使用 {file_path.name} 覆盖之前的 {prev_file}"
                )
                previous_values = replacement_by_pokemon[pokemon_id]
                stats["inserted_native"] -= sum(1 for _, _, skill_type, _ in previous_values if skill_type == NATIVE_SKILL_TYPE)
                stats["inserted_learn"] -= sum(1 for _, _, skill_type, _ in previous_values if skill_type == LEARN_SKILL_TYPE)
                stats["inserted_rows"] -= len(previous_values)
            else:
                stats["replaced_pokemon"] += 1

            current_values = native_values + learn_values
            replacement_by_pokemon[pokemon_id] = current_values
            replacement_source_file[pokemon_id] = file_path.name
            stats["inserted_native"] += len(native_values)
            stats["inserted_learn"] += len(learn_values)
            stats["inserted_rows"] += len(current_values)

        _done(
            f"扫描完成 files={stats['files']} replaced_pokemon={stats['replaced_pokemon']} "
            f"inserted_rows={stats['inserted_rows']} "
            f"({time.time() - t:.2f}s)"
        )

        replaced_pokemon_ids = sorted(replacement_by_pokemon.keys())
        replacement_values = [
            row
            for pokemon_id in replaced_pokemon_ids
            for row in replacement_by_pokemon[pokemon_id]
        ]

        if replaced_pokemon_ids:
            t = _step("替换 pokemon_skill")
            stats["deleted_old_rows"] = _count_existing_rows(cur, replaced_pokemon_ids)
            cur.execute(
                "DELETE FROM pokemon_skill WHERE pokemon_id = ANY(%s)",
                (replaced_pokemon_ids,),
            )
            if replacement_values:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO pokemon_skill (pokemon_id, skill_id, type, sort_order)
                    VALUES %s
                    """,
                    replacement_values,
                    page_size=1000,
                )
            _done(
                f"pokemon={len(replaced_pokemon_ids)} deleted_old_rows={stats['deleted_old_rows']} "
                f"inserted_rows={stats['inserted_rows']} ({time.time() - t:.2f}s)"
            )
        else:
            print("\n[>>] 无可替换精灵，跳过写库", flush=True)

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

    print("\n[summary]", flush=True)
    print(
        "  "
        f"files={stats['files']} invalid_json={stats['invalid_json']} invalid_entries={stats['invalid_entries']} "
        f"missing_name_en={stats['missing_name_en']} missing_pokemon={stats['missing_pokemon']} "
        f"ambiguous_pokemon={stats['ambiguous_pokemon']}",
        flush=True,
    )
    print(
        "  "
        f"missing_skill={stats['missing_skill']} ambiguous_skill={stats['ambiguous_skill']} "
        f"duplicate_skill_in_json={stats['duplicate_skill_in_json']} "
        f"duplicate_pokemon_json={stats['duplicate_pokemon_json']}",
        flush=True,
    )
    print(
        "  "
        f"replaced_pokemon={stats['replaced_pokemon']} deleted_old_rows={stats['deleted_old_rows']} "
        f"inserted_native={stats['inserted_native']} inserted_learn={stats['inserted_learn']} "
        f"inserted_rows={stats['inserted_rows']} elapsed={time.time() - total_start:.2f}s",
        flush=True,
    )

    _warn_list("pokemon.name_en 为空（仅提示，不影响本次匹配）", warnings["pokemon_without_name_en"])
    _warn_list("无效 JSON", warnings["invalid_json"])
    _warn_list("无效技能条目", warnings["invalid_entries"])
    _warn_list("JSON 缺少根级 name", warnings["missing_name_en"])
    _warn_list("未匹配到精灵", warnings["missing_pokemon"])
    _warn_list("匹配到多个精灵", warnings["ambiguous_pokemon"])
    _warn_list("未匹配到技能", warnings["missing_skill"])
    _warn_list("匹配到多个技能", warnings["ambiguous_skill"])
    _warn_list("同一 JSON 内重复技能（已按优先级去重）", warnings["duplicate_skill_in_json"])
    _warn_list("同一精灵被多个 JSON 命中（已用后者覆盖前者）", warnings["duplicate_pokemon_json"])


if __name__ == "__main__":
    main()
