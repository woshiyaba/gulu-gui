"""
从 docs/pets/属性.json 导入属性轴顺序与单方受击倍率矩阵，写入 attribute_axis / attribute_matchup。

规则（与 JSON 语义一致）：
- 「被克制」：该防守属性被列出的进攻属性攻击时，受到 2 倍伤害（单方乘 2）。
- 「抵抗」：受到 0.5 倍伤害（单方乘 0.5）。
- 未出现在两侧列表中的进攻属性：倍率为 1。
- 精灵双属性时，接口层对两个单方倍率相乘（与常见属性相克表一致）。

用法：
    uv run python scripts/import_attribute_matchups.py

全量重建 main.py 时会在末尾自动执行本脚本。
"""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_conn

JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "pets",
    "属性.json",
)

DDL_AXIS = """
CREATE TABLE IF NOT EXISTS attribute_axis (
    attr_name  VARCHAR(20) NOT NULL COMMENT '属性名，与 pokemon_attribute.attr_name 对齐',
    sort_order INT          NOT NULL COMMENT '表头从左到右顺序，从 1 开始',
    PRIMARY KEY (attr_name),
    UNIQUE KEY uk_attr_axis_sort (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='属性表头顺序（与 docs/pets/属性.json 键顺序一致）';
"""

DDL_MATCHUP = """
CREATE TABLE IF NOT EXISTS attribute_matchup (
    defender_attr VARCHAR(20) NOT NULL COMMENT '受击方（精灵）的某一属性',
    attacker_attr VARCHAR(20) NOT NULL COMMENT '进攻招式属性',
    multiplier      DECIMAL(10, 8) NOT NULL COMMENT '该单方属性下受击倍率：2 / 1 / 0.5',
    PRIMARY KEY (defender_attr, attacker_attr),
    KEY idx_matchup_defender (defender_attr),
    KEY idx_matchup_attacker (attacker_attr)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单方属性受击倍率（由属性.json 生成）';
"""


def _single_multiplier(entry: dict[str, Any], attacker: str) -> Decimal:
    weak = set(entry.get("被克制") or [])
    resist = set(entry.get("抵抗") or [])
    m = Decimal("1")
    if attacker in weak:
        m *= Decimal("2")
    if attacker in resist:
        m *= Decimal("0.5")
    return m


def main() -> None:
    with open(JSON_PATH, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    axis = list(data.keys())
    if not axis:
        raise SystemExit("属性.json 为空")

    matchup_rows: list[tuple[str, str, Decimal]] = []
    for defender in axis:
        entry = data[defender]
        for attacker in axis:
            matchup_rows.append((defender, attacker, _single_multiplier(entry, attacker)))

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(DDL_AXIS)
            cur.execute(DDL_MATCHUP)
            cur.execute("DELETE FROM attribute_matchup")
            cur.execute("DELETE FROM attribute_axis")

            cur.executemany(
                "INSERT INTO attribute_axis (attr_name, sort_order) VALUES (%s, %s)",
                [(name, i + 1) for i, name in enumerate(axis)],
            )
            cur.executemany(
                "INSERT INTO attribute_matchup (defender_attr, attacker_attr, multiplier) VALUES (%s, %s, %s)",
                matchup_rows,
            )
        conn.commit()
        print(
            f"[import_attribute_matchups] axis={len(axis)} 项, matchup={len(matchup_rows)} 条, 来源 {JSON_PATH}",
            flush=True,
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
