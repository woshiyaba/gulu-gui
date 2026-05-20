"""
从 rococ.cn:227 接口爬取精灵基础信息与三类技能，落库到 PostgreSQL。

数据流：
  pet/getPetByNum/{num}   → 精灵基础信息 + 特性 + 主/副属性
  skill/petSkill/{skills}/1 → 原生技能   → skill + pokemon_skill
  skill/petSkill/{skills}/2 → 血脉技能   → skill + pokemon_skill
  skill/petSkill/{skills}/3 → 技能石技能 → skill + pokemon_skill

规则：
- 特性 (pn/pd) 先 upsert 到 pokemon_trait，再绑定到 pokemon.trait_id
- 技能按 name 查 skill；未命中则按接口数据新建 skill 后再绑定 pokemon_skill
- 同一只精灵每次运行会先清掉旧的 pokemon_attribute / pokemon_skill 再重写

用法：
    uv run python scripts/import_rococ_pokemon.py
    uv run python scripts/import_rococ_pokemon.py --start 348 --end 400
    uv run python scripts/import_rococ_pokemon.py --start 348 --max-empty 5
    uv run python scripts/import_rococ_pokemon.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras
import requests
import urllib3

from config import PG_CONFIG


BASE_URL = "https://rococ.cn:227"
PET_URL = f"{BASE_URL}/pet/getPetByNum"
SKILL_URL = f"{BASE_URL}/skill/petSkill"

# 接口字段 pa / sa / atbe → attribute.id 映射
# 9 / 13 文档未给出，依据 sql/attribute.sql 中现有数据兜底
ATTR_ID_BY_API_CODE: dict[int, int] = {
    1: 7,    # 普通
    2: 3,    # 草
    3: 1,    # 火
    4: 2,    # 水
    5: 4,    # 光
    6: 8,    # 地
    7: 9,    # 冰
    8: 10,   # 龙
    9: 11,   # 电
    10: 12,  # 毒
    11: 13,  # 虫
    12: 14,  # 武
    13: 15,  # 翼
    14: 16,  # 萌
    15: 6,   # 幽
    16: 5,   # 恶
    17: 17,  # 机
    18: 18,  # 幻
}

# 接口字段 type → skill.type 字面值
SKILL_TYPE_LABEL: dict[int, str] = {
    1: "物攻",
    2: "魔攻",
    3: "状态",
    4: "防御",
}

CLUSTER_TOKEN_RE = re.compile(r"\[\s*([^\[\]]+?)\s*\]")
CLUSTER_SKIP_TOKENS = {"未知", ""}

NATIVE_SKILL_TYPE = "原生技能"
BLOOD_SKILL_TYPE = "血脉技能"
MACHINE_SKILL_TYPE = "技能石技能"

SKILL_SOURCES: list[tuple[int, str]] = [
    (1, NATIVE_SKILL_TYPE),
    (2, BLOOD_SKILL_TYPE),
    (3, MACHINE_SKILL_TYPE),
]

COMMON_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Content-Type": "application/json",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://servicewechat.com/wx148bb2bfc2507229/41/page-frame.html",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 "
        "MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI "
        "MiniProgramEnv/Windows WindowsWechat/WMPF "
        "WindowsWechat(0x63090c37)XWEB/14185"
    ),
    "xweb_xhr": "1",
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


def _clean_str(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _parse_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = _clean_str(value)
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        try:
            return int(float(text))
        except ValueError:
            return default


def _build_session(verify_ssl: bool) -> requests.Session:
    session = requests.Session()
    session.headers.update(COMMON_HEADERS)
    session.verify = verify_ssl
    return session


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(**PG_CONFIG)


def fetch_pet(session: requests.Session, num: int) -> dict[str, Any] | None:
    resp = session.get(f"{PET_URL}/{num}", timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 200:
        raise RuntimeError(f"getPetByNum/{num} 返回异常: {payload}")
    data = payload.get("data") or []
    if not data:
        return None
    return data[0]


def fetch_skills(
    session: requests.Session, skill_group_id: int, kind: int
) -> list[dict[str, Any]]:
    resp = session.get(f"{SKILL_URL}/{skill_group_id}/{kind}", timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 200:
        raise RuntimeError(
            f"petSkill/{skill_group_id}/{kind} 返回异常: {payload}"
        )
    return payload.get("data") or []


def upsert_pokemon_trait(cur, name: str, description: str) -> int:
    cur.execute(
        """
        INSERT INTO pokemon_trait (name, description)
        VALUES (%s, %s)
        ON CONFLICT (name) DO UPDATE
          SET description = EXCLUDED.description
        RETURNING id
        """,
        (name, description),
    )
    return int(cur.fetchone()["id"])


def find_pokemon_id_by_no(cur, no: str) -> int | None:
    cur.execute("SELECT id FROM pokemon WHERE no = %s LIMIT 1", (no,))
    row = cur.fetchone()
    return int(row["id"]) if row else None


def upsert_pokemon(
    cur, pet: dict[str, Any], trait_id: int
) -> tuple[int, bool]:
    """返回 (pokemon_id, is_insert)。"""
    num = _parse_int(pet.get("num"))
    no = f"NO.{num}"
    name = _clean_str(pet.get("name"))
    hp = _parse_int(pet.get("hp"))
    atk = _parse_int(pet.get("ad"))
    matk = _parse_int(pet.get("ap"))
    def_val = _parse_int(pet.get("def"))
    mdef = _parse_int(pet.get("mnd"))
    spd = _parse_int(pet.get("spd"))
    total_race = hp + atk + matk + def_val + mdef + spd
    obtain = _clean_str(pet.get("obtain"))

    existing_id = find_pokemon_id_by_no(cur, no)
    if existing_id is not None:
        cur.execute(
            """
            UPDATE pokemon
               SET name          = %s,
                   trait_id      = %s,
                   hp            = %s,
                   atk           = %s,
                   matk          = %s,
                   def_val       = %s,
                   mdef          = %s,
                   spd           = %s,
                   total_race    = %s,
                   obtain_method = %s
             WHERE id = %s
            """,
            (name, trait_id, hp, atk, matk, def_val, mdef, spd, total_race, obtain, existing_id),
        )
        return existing_id, False

    cur.execute(
        """
        INSERT INTO pokemon
            (no, name, trait_id, hp, atk, matk, def_val, mdef, spd,
             total_race, obtain_method)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (no, name, trait_id, hp, atk, matk, def_val, mdef, spd, total_race, obtain),
    )
    return int(cur.fetchone()["id"]), True


def replace_pokemon_attributes(
    cur, pokemon_id: int, attr_ids: list[int]
) -> int:
    cur.execute("DELETE FROM pokemon_attribute WHERE pokemon_id = %s", (pokemon_id,))
    inserted = 0
    for attr_id in attr_ids:
        cur.execute(
            """
            INSERT INTO pokemon_attribute (pokemon_id, attr_id)
            VALUES (%s, %s)
            ON CONFLICT (pokemon_id, attr_id) DO NOTHING
            """,
            (pokemon_id, attr_id),
        )
        if cur.rowcount:
            inserted += 1
    return inserted


def get_skill_id_by_name(cur, name: str) -> int | None:
    cur.execute("SELECT id FROM skill WHERE name = %s LIMIT 1", (name,))
    row = cur.fetchone()
    return int(row["id"]) if row else None


def insert_skill(cur, entry: dict[str, Any]) -> int:
    name = _clean_str(entry.get("name"))
    attr_id = ATTR_ID_BY_API_CODE.get(_parse_int(entry.get("atbe"))) or None
    power = _parse_int(entry.get("value"))  # "--" → 0
    type_label = SKILL_TYPE_LABEL.get(_parse_int(entry.get("type")), "")
    consume = _parse_int(entry.get("energy"))
    desc = _clean_str(entry.get("role"))
    icon = _clean_str(entry.get("img"))

    cur.execute(
        """
        INSERT INTO skill (name, attr_id, power, type, consume, skill_desc, icon)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (name) DO UPDATE
          SET attr_id    = COALESCE(skill.attr_id, EXCLUDED.attr_id),
              power      = EXCLUDED.power,
              type       = EXCLUDED.type,
              consume    = EXCLUDED.consume,
              skill_desc = EXCLUDED.skill_desc,
              icon       = CASE WHEN skill.icon = '' THEN EXCLUDED.icon ELSE skill.icon END
        RETURNING id
        """,
        (name, attr_id, power, type_label, consume, desc, icon),
    )
    return int(cur.fetchone()["id"])


def replace_pokemon_skills(
    cur,
    session: requests.Session,
    pokemon_id: int,
    skill_group_id: int,
    sleep_seconds: float,
) -> dict[str, int]:
    stats = {
        "skill_total": 0,
        "skill_matched": 0,
        "skill_inserted": 0,
        "link_inserted": 0,
        "deleted_old_rows": 0,
    }

    cur.execute(
        "DELETE FROM pokemon_skill WHERE pokemon_id = %s RETURNING id",
        (pokemon_id,),
    )
    stats["deleted_old_rows"] = len(cur.fetchall())

    seen_skill_ids: set[int] = set()
    for kind, source_label in SKILL_SOURCES:
        entries = fetch_skills(session, skill_group_id, kind)
        for sort_order, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                continue
            skill_name = _clean_str(entry.get("name"))
            if not skill_name:
                continue
            stats["skill_total"] += 1

            existing_id = get_skill_id_by_name(cur, skill_name)
            if existing_id is not None:
                skill_id = existing_id
                stats["skill_matched"] += 1
            else:
                skill_id = insert_skill(cur, entry)
                stats["skill_inserted"] += 1

            if skill_id in seen_skill_ids:
                continue
            seen_skill_ids.add(skill_id)

            cur.execute(
                """
                INSERT INTO pokemon_skill (pokemon_id, skill_id, type, sort_order)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (pokemon_id, skill_id) DO UPDATE
                  SET type       = EXCLUDED.type,
                      sort_order = EXCLUDED.sort_order
                """,
                (pokemon_id, skill_id, source_label, sort_order),
            )
            stats["link_inserted"] += 1

        time.sleep(sleep_seconds)

    return stats


def parse_egg_groups(cluster: str) -> list[str]:
    """从 cluster 字段（形如 "[ 妖精 ]， [ 拟人 ]"）抽取蛋组名并拼接「组」后缀。"""
    group_names: list[str] = []
    for token in CLUSTER_TOKEN_RE.findall(cluster or ""):
        name = token.strip()
        if name in CLUSTER_SKIP_TOKENS:
            continue
        group_name = f"{name}组"
        if group_name not in group_names:
            group_names.append(group_name)
    return group_names


def replace_pokemon_egg_groups(
    cur, pokemon_id: int, group_names: list[str]
) -> int:
    cur.execute(
        "DELETE FROM pokemon_egg_group WHERE pokemon_id = %s", (pokemon_id,)
    )
    inserted = 0
    for group_name in group_names:
        cur.execute(
            """
            INSERT INTO pokemon_egg_group (pokemon_id, group_name)
            VALUES (%s, %s)
            ON CONFLICT (pokemon_id, group_name) DO NOTHING
            """,
            (pokemon_id, group_name),
        )
        if cur.rowcount:
            inserted += 1
    return inserted


def collect_attr_ids(pet: dict[str, Any], warnings: list[str], num: int) -> list[int]:
    ids: list[int] = []
    for field in ("pa", "sa"):
        code = _parse_int(pet.get(field))
        if code == 0:
            continue
        attr_id = ATTR_ID_BY_API_CODE.get(code)
        if attr_id is None:
            warnings.append(f"num={num} {field}={code} 未在属性映射中找到")
            continue
        if attr_id not in ids:
            ids.append(attr_id)
    return ids


def process_num(
    cur,
    session: requests.Session,
    num: int,
    *,
    sleep_seconds: float,
    warnings: dict[str, list[str]],
    stats: dict[str, int],
    egg_groups_only: bool = False,
) -> bool:
    """处理单个 num。返回 False 表示该 num 数据为空。"""
    pet = fetch_pet(session, num)
    if pet is None:
        return False

    name = _clean_str(pet.get("name"))
    if not name:
        warnings["missing_name"].append(f"num={num} 接口未返回精灵名")
        return True

    if egg_groups_only:
        no = f"NO.{num}"
        pokemon_id = find_pokemon_id_by_no(cur, no)
        if pokemon_id is None:
            warnings["missing_pokemon"].append(
                f"num={num} name={name!r} 库中未找到 no={no!r}，已跳过蛋组同步"
            )
            return True
        cluster = _clean_str(pet.get("cluster"))
        egg_groups = parse_egg_groups(cluster)
        if not egg_groups:
            warnings["missing_egg_group"].append(
                f"num={num} name={name!r} cluster={cluster!r} 未解析到蛋组"
            )
        inserted_egg_groups = replace_pokemon_egg_groups(cur, pokemon_id, egg_groups)
        stats["egg_group_inserted"] += inserted_egg_groups
        print(
            f"    [num={num}] name={name!r} pokemon_id={pokemon_id} "
            f"egg_groups={egg_groups} (egg-groups-only)",
            flush=True,
        )
        return True

    trait_name = _clean_str(pet.get("pn"))
    trait_desc = _clean_str(pet.get("pd"))
    if not trait_name:
        warnings["missing_trait"].append(f"num={num} name={name!r} 接口未返回特性")
        return True

    trait_id = upsert_pokemon_trait(cur, trait_name, trait_desc)
    pokemon_id, is_insert = upsert_pokemon(cur, pet, trait_id)
    if is_insert:
        stats["pokemon_inserted"] += 1
    else:
        stats["pokemon_updated"] += 1

    attr_ids = collect_attr_ids(pet, warnings["missing_attribute"], num)
    if not attr_ids:
        warnings["missing_attribute"].append(f"num={num} 无可用属性映射")
    replace_pokemon_attributes(cur, pokemon_id, attr_ids)

    cluster = _clean_str(pet.get("cluster"))
    egg_groups = parse_egg_groups(cluster)
    if not egg_groups:
        warnings["missing_egg_group"].append(
            f"num={num} name={name!r} cluster={cluster!r} 未解析到蛋组"
        )
    inserted_egg_groups = replace_pokemon_egg_groups(cur, pokemon_id, egg_groups)
    stats["egg_group_inserted"] += inserted_egg_groups

    skill_group_id = _parse_int(pet.get("skills"))
    if skill_group_id <= 0:
        warnings["missing_skill_group"].append(
            f"num={num} name={name!r} skills 字段缺失或为 0"
        )
        return True

    print(
        f"    [num={num}] name={name!r} pokemon_id={pokemon_id} "
        f"trait_id={trait_id} skill_group={skill_group_id} "
        f"attrs={attr_ids} egg_groups={egg_groups}",
        flush=True,
    )
    skill_stats = replace_pokemon_skills(
        cur, session, pokemon_id, skill_group_id, sleep_seconds
    )
    stats["skill_total"] += skill_stats["skill_total"]
    stats["skill_matched"] += skill_stats["skill_matched"]
    stats["skill_inserted"] += skill_stats["skill_inserted"]
    stats["link_inserted"] += skill_stats["link_inserted"]
    stats["pokemon_skill_deleted"] += skill_stats["deleted_old_rows"]
    return True


def main() -> None:
    _ensure_utf8_stdout()

    parser = argparse.ArgumentParser(
        description="从 rococ.cn:227 拉取精灵与三类技能落库到 PostgreSQL"
    )
    parser.add_argument("--start", type=int, default=348, help="起始 num（默认 348）")
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="结束 num（包含），默认无上限，由 --max-empty 触发停止",
    )
    parser.add_argument(
        "--max-empty",
        type=int,
        default=5,
        help="连续空响应多少次后停止（默认 5）",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.3,
        help="每次接口请求之间的休眠秒数（默认 0.3）",
    )
    parser.add_argument("--dry-run", action="store_true", help="执行后回滚，不真正写库")
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="禁用 SSL 证书校验（rococ.cn:227 为非标准端口时可能需要）",
    )
    parser.add_argument(
        "--egg-groups-only",
        action="store_true",
        help="只同步蛋组（pokemon_egg_group）：跳过特性/精灵/属性/技能写入和技能接口请求",
    )
    args = parser.parse_args()

    if args.no_verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    total_start = time.time()
    print("=" * 60)
    print("  导入 rococ.cn:227 精灵 & 技能 → PostgreSQL")
    print(
        f"  start={args.start} end={args.end} max_empty={args.max_empty} "
        f"sleep={args.sleep} dry_run={args.dry_run} verify_ssl={not args.no_verify_ssl} "
        f"egg_groups_only={args.egg_groups_only}"
    )
    print("=" * 60)

    session = _build_session(verify_ssl=not args.no_verify_ssl)

    stats = {
        "processed": 0,
        "empty": 0,
        "pokemon_inserted": 0,
        "pokemon_updated": 0,
        "skill_total": 0,
        "skill_matched": 0,
        "skill_inserted": 0,
        "link_inserted": 0,
        "pokemon_skill_deleted": 0,
        "egg_group_inserted": 0,
    }
    warnings: dict[str, list[str]] = {
        "missing_name": [],
        "missing_trait": [],
        "missing_attribute": [],
        "missing_egg_group": [],
        "missing_skill_group": [],
        "missing_pokemon": [],
        "fetch_failed": [],
    }

    conn = pg_conn()
    conn.autocommit = False

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        t = _step("循环拉取并落库")
        num = args.start
        empty_streak = 0
        while True:
            if args.end is not None and num > args.end:
                break

            try:
                has_data = process_num(
                    cur,
                    session,
                    num,
                    sleep_seconds=args.sleep,
                    warnings=warnings,
                    stats=stats,
                    egg_groups_only=args.egg_groups_only,
                )
            except Exception as exc:
                warnings["fetch_failed"].append(f"num={num} err={exc}")
                print(f"    [error] num={num} {exc}", flush=True)
                empty_streak = 0
                num += 1
                time.sleep(args.sleep)
                continue

            if not has_data:
                stats["empty"] += 1
                empty_streak += 1
                print(f"    [skip] num={num} 接口返回空数据", flush=True)
                if args.end is None and empty_streak >= args.max_empty:
                    print(
                        f"    [stop] 连续 {empty_streak} 次空响应，结束循环",
                        flush=True,
                    )
                    break
            else:
                stats["processed"] += 1
                empty_streak = 0

            num += 1
            time.sleep(args.sleep)

        _done(
            f"processed={stats['processed']} empty={stats['empty']} "
            f"pokemon_inserted={stats['pokemon_inserted']} "
            f"pokemon_updated={stats['pokemon_updated']} "
            f"egg_group_inserted={stats['egg_group_inserted']} "
            f"skills_total={stats['skill_total']} "
            f"skill_matched={stats['skill_matched']} "
            f"skill_inserted={stats['skill_inserted']} "
            f"link_inserted={stats['link_inserted']} "
            f"pokemon_skill_deleted={stats['pokemon_skill_deleted']} "
            f"({time.time() - t:.2f}s)"
        )

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

    _warn_list("接口未返回精灵名", warnings["missing_name"])
    _warn_list("接口未返回特性", warnings["missing_trait"])
    _warn_list("属性映射缺失", warnings["missing_attribute"])
    _warn_list("cluster 未解析到蛋组", warnings["missing_egg_group"])
    _warn_list("skills 字段缺失或为 0", warnings["missing_skill_group"])
    _warn_list("库中未找到对应精灵（蛋组模式）", warnings["missing_pokemon"])
    _warn_list("接口请求失败", warnings["fetch_failed"])

    print(
        f"\n[summary] elapsed={time.time() - total_start:.2f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
