"""
读取 docs/breed/PET_EGG_CONF.json，重建 egg_hatch_pet 表。
记录每种蛋可孵化哪些宠物，支持按蛋类型查询。

蛋分三类：
  precious - 特殊蛋（有 precious_egg_type 字段，原始值 1~7，含义待确认）
  random   - 随机蛋（有 random_eggs_group，按 effect 值分池）
  normal   - 普通蛋（以上字段均无）

用法：
    uv run python scripts/import_egg_hatch.py
"""

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_conn

JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "breed", "PET_EGG_CONF.json",
)

DDL = """
CREATE TABLE IF NOT EXISTS egg_hatch_pet (
    id                  INT          NOT NULL AUTO_INCREMENT,
    egg_category        VARCHAR(20)  NOT NULL COMMENT 'precious / random / normal',
    egg_type_id         INT          NOT NULL COMMENT '特殊蛋:precious_egg_type原始值; 随机蛋:effect原始值; 普通蛋:0',
    pet_id              INT          NOT NULL COMMENT '宠物ID',
    pet_name            VARCHAR(50)  NOT NULL COMMENT '宠物名称',
    form                VARCHAR(100) DEFAULT NULL COMMENT '宠物形态名（原始字段 form）',
    hatch_data          INT          NOT NULL DEFAULT 0  COMMENT '孵化时间（秒）',
    weight_low          INT          NOT NULL DEFAULT 0  COMMENT '体重下限（g）',
    weight_high         INT          NOT NULL DEFAULT 0  COMMENT '体重上限（g）',
    height_low          INT          NOT NULL DEFAULT 0  COMMENT '身高下限（cm）',
    height_high         INT          NOT NULL DEFAULT 0  COMMENT '身高上限（cm）',
    random_weight       INT          DEFAULT NULL        COMMENT '随机蛋专用：random_eggs_group.random_weight 原始值',
    glass_prob_num      INT          DEFAULT NULL        COMMENT 'egg_base_glass_prob_array[0]',
    glass_prob_denom    INT          DEFAULT NULL        COMMENT 'egg_base_glass_prob_array[1]',
    glass_add_num       INT          DEFAULT NULL        COMMENT 'egg_add_glass_prob_array[0]',
    glass_add_denom     INT          DEFAULT NULL        COMMENT 'egg_add_glass_prob_array[1]',
    contact_glass       TINYINT(1)   DEFAULT NULL        COMMENT 'is_contact_add_glass_prob',
    shining_prob_num    INT          DEFAULT NULL        COMMENT 'egg_base_shining_prob_array[0]',
    shining_prob_denom  INT          DEFAULT NULL        COMMENT 'egg_base_shining_prob_array[1]',
    shining_add_num     INT          DEFAULT NULL        COMMENT 'egg_add_shining_prob_array[0]',
    shining_add_denom   INT          DEFAULT NULL        COMMENT 'egg_add_shining_prob_array[1]',
    contact_shining     TINYINT(1)   DEFAULT NULL        COMMENT 'is_contact_add_shining_prob',
    PRIMARY KEY (id),
    KEY idx_egg (egg_category, egg_type_id),
    KEY idx_pet_id (pet_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='蛋孵化宠物关系表';
"""


def _create_table(cur) -> None:
    cur.execute("DROP TABLE IF EXISTS egg_hatch_pet")
    cur.execute(DDL)
    print("[migrate] egg_hatch_pet 表已重建")


def _extract_prob(arr: list | None, idx: int) -> int | None:
    """安全取概率数组的指定位置，数组不存在时返回 None。"""
    if arr and len(arr) > idx:
        return arr[idx]
    return None


def _build_base(pet: dict) -> dict:
    """提取每条宠物记录的公共字段。"""
    glass = pet.get("egg_base_glass_prob_array")
    glass_add = pet.get("egg_add_glass_prob_array")
    shining = pet.get("egg_base_shining_prob_array")
    shining_add = pet.get("egg_add_shining_prob_array")

    return {
        "pet_id":             pet["pet_id"],
        "pet_name":           pet["name"],
        "form":               pet.get("form"),
        "hatch_data":         pet.get("hatch_data", 0),
        "weight_low":         pet.get("weight_low", 0),
        "weight_high":        pet.get("weight_high", 0),
        "height_low":         pet.get("height_low", 0),
        "height_high":        pet.get("height_high", 0),
        "glass_prob_num":     _extract_prob(glass, 0),
        "glass_prob_denom":   _extract_prob(glass, 1),
        "glass_add_num":      _extract_prob(glass_add, 0),
        "glass_add_denom":    _extract_prob(glass_add, 1),
        "contact_glass":      pet.get("is_contact_add_glass_prob"),
        "shining_prob_num":   _extract_prob(shining, 0),
        "shining_prob_denom": _extract_prob(shining, 1),
        "shining_add_num":    _extract_prob(shining_add, 0),
        "shining_add_denom":  _extract_prob(shining_add, 1),
        "contact_shining":    pet.get("is_contact_add_shining_prob"),
    }


def _parse_records(conf: list[dict]) -> list[dict]:
    """
    将 PET_EGG_CONF 展开为「蛋→宠物」关系行。
    一只宠物出现在多个随机蛋池时会产生多行。
    """
    records = []

    for pet in conf:
        base = _build_base(pet)
        precious = pet.get("precious_egg_type")
        rand_groups = pet.get("random_eggs_group")

        if precious is not None:
            records.append({
                **base,
                "egg_category":  "precious",
                "egg_type_id":   precious,
                "random_weight": None,
            })
        elif rand_groups:
            # 一只宠物可能出现在多个 effect 池中，展开为多行
            for group in rand_groups:
                records.append({
                    **base,
                    "egg_category":  "random",
                    "egg_type_id":   group["effect"],
                    "random_weight": group["random_weight"],
                })
        else:
            records.append({
                **base,
                "egg_category":  "normal",
                "egg_type_id":   0,
                "random_weight": None,
            })

    return records


def _batch_insert(cur, records: list[dict]) -> int:
    """批量插入，返回插入行数。"""
    sql = """
        INSERT INTO egg_hatch_pet (
            egg_category, egg_type_id,
            pet_id, pet_name, form, hatch_data,
            weight_low, weight_high, height_low, height_high,
            random_weight,
            glass_prob_num, glass_prob_denom,
            glass_add_num, glass_add_denom, contact_glass,
            shining_prob_num, shining_prob_denom,
            shining_add_num, shining_add_denom, contact_shining
        ) VALUES (
            %(egg_category)s, %(egg_type_id)s,
            %(pet_id)s, %(pet_name)s, %(form)s, %(hatch_data)s,
            %(weight_low)s, %(weight_high)s, %(height_low)s, %(height_high)s,
            %(random_weight)s,
            %(glass_prob_num)s, %(glass_prob_denom)s,
            %(glass_add_num)s, %(glass_add_denom)s, %(contact_glass)s,
            %(shining_prob_num)s, %(shining_prob_denom)s,
            %(shining_add_num)s, %(shining_add_denom)s, %(contact_shining)s
        )
    """
    cur.executemany(sql, records)
    return len(records)


def main() -> None:
    with open(JSON_PATH, encoding="utf-8") as f:
        conf = json.load(f)
    print(f"[info] 共读取 {len(conf)} 条宠物蛋配置")

    records = _parse_records(conf)

    cat_count = Counter(r["egg_category"] for r in records)
    print(f"[info] precious={cat_count['precious']}, "
          f"random={cat_count['random']}, normal={cat_count['normal']}")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            _create_table(cur)
            inserted = _batch_insert(cur, records)
        conn.commit()
        print(f"[done] 共插入 {inserted} 行到 egg_hatch_pet")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
