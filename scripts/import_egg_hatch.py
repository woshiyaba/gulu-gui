"""
从 pokemon_detail 读取 pokemon_name，在 Pets.json 中查找匹配的中文名，
将 is_leader_form 和 breeding 孵化/体型数据写入 egg_hatch_pet 表。

用法：
    uv run python scripts/import_egg_hatch.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_conn

PETS_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "pets", "Pets.json",
)

DDL = """
CREATE TABLE IF NOT EXISTS egg_hatch_pet (
    id              INT          NOT NULL AUTO_INCREMENT,
    pokemon_name    VARCHAR(50)  NOT NULL COMMENT '宠物名称（含括号变种原始值）',
    is_leader_form  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否首领形态',
    hatch_data      INT          NOT NULL DEFAULT 0  COMMENT '孵化时间（秒）',
    weight_low      INT          NOT NULL DEFAULT 0  COMMENT '体重下限（g）',
    weight_high     INT          NOT NULL DEFAULT 0  COMMENT '体重上限（g）',
    height_low      INT          NOT NULL DEFAULT 0  COMMENT '身高下限（cm）',
    height_high     INT          NOT NULL DEFAULT 0  COMMENT '身高上限（cm）',
    PRIMARY KEY (id),
    KEY idx_pokemon_name (pokemon_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='蛋孵化宠物数据';
"""


def _strip_parentheses(name: str) -> str:
    """去掉中文括号及其内容：'迪莫（光系血脉）' → '迪莫'"""
    return re.sub(r'（[^）]*）', '', name).strip()


def _build_pets_map(pets: list) -> dict:
    """构建 {zh_name: pet_entry} 映射，供快速查找。"""
    result = {}
    for pet in pets:
        zh_name = pet.get("localized", {}).get("zh", {}).get("name")
        if zh_name:
            result[zh_name] = pet
    return result


def _fetch_pokemon_names(cur) -> list:
    """从 pokemon_detail 查询所有 pokemon_name。"""
    cur.execute("SELECT pokemon_name FROM pokemon_detail")
    return [row["pokemon_name"] for row in cur.fetchall()]


def _build_records(pokemon_names: list, pets_map: dict) -> tuple:
    """
    对每个 pokemon_name 查找 Pets.json，构建待插入记录。
    返回 (records, missed_names)。
    """
    records = []
    missed = []

    for name in pokemon_names:
        base_name = _strip_parentheses(name)
        pet = pets_map.get(base_name)
        if pet is None:
            missed.append(name)
            continue

        breeding = pet.get("breeding") or {}
        records.append({
            "pokemon_name":   name,
            "is_leader_form": 1 if pet.get("is_leader_form") else 0,
            "hatch_data":     breeding.get("hatch_data", 0),
            "weight_low":     breeding.get("weight_low", 0),
            "weight_high":    breeding.get("weight_high", 0),
            "height_low":     breeding.get("height_low", 0),
            "height_high":    breeding.get("height_high", 0),
        })

    return records, missed


def _create_table(cur) -> None:
    cur.execute("DROP TABLE IF EXISTS egg_hatch_pet")
    cur.execute(DDL)
    print("[migrate] egg_hatch_pet 表已重建")


def _batch_insert(cur, records: list) -> int:
    sql = """
        INSERT INTO egg_hatch_pet (
            pokemon_name, is_leader_form,
            hatch_data, weight_low, weight_high, height_low, height_high
        ) VALUES (
            %(pokemon_name)s, %(is_leader_form)s,
            %(hatch_data)s, %(weight_low)s, %(weight_high)s,
            %(height_low)s, %(height_high)s
        )
    """
    cur.executemany(sql, records)
    return len(records)


def main() -> None:
    with open(PETS_JSON_PATH, encoding="utf-8") as f:
        pets = json.load(f)
    print(f"[info] Pets.json 共 {len(pets)} 条宠物数据")

    pets_map = _build_pets_map(pets)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            _create_table(cur)
            pokemon_names = _fetch_pokemon_names(cur)
            print(f"[info] pokemon_detail 共 {len(pokemon_names)} 条记录")

            records, missed = _build_records(pokemon_names, pets_map)

            if missed:
                print(f"[warn] 以下 {len(missed)} 个宠物在 Pets.json 中未找到匹配：")
                for m in missed:
                    print(f"  - {m}")

            inserted = _batch_insert(cur, records) if records else 0

        conn.commit()
        print(f"[done] 共插入 {inserted} 行到 egg_hatch_pet")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
