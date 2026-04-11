"""
从 docs/pets/洛克王国宠物蛋组.json 导入蛋组：按 JSON 中的简称查 pokemon.id，一对多写入 pokemon_egg_group。

名称对齐：JSON 无中文括号后缀；库中可能有「星光狮（星光能量的样子）」等形态。
先精确匹配 name，再匹配「简称 + （…」」的所有行，为每条 pokemon 写入相同蛋组。

用法：
    uv run python scripts/import_egg_groups.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_conn

JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "pets",
    "洛克王国宠物蛋组.json",
)

DDL = """
CREATE TABLE IF NOT EXISTS pokemon_egg_group (
    id           INT          NOT NULL AUTO_INCREMENT,
    pokemon_id   INT          NOT NULL COMMENT '关联 pokemon.id',
    group_name   VARCHAR(50)  NOT NULL COMMENT '蛋组名称',
    PRIMARY KEY (id),
    UNIQUE KEY uk_pokemon_group (pokemon_id, group_name),
    KEY idx_group_name (group_name),
    CONSTRAINT fk_peg_pokemon FOREIGN KEY (pokemon_id) REFERENCES pokemon (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='精灵蛋组（多对一 pokemon）';
"""

_BATCH = 500

# JSON 蛋组名无全角括号形态后缀；与库中「某某（…）」对齐
_SQL_IDS_BY_BASE_NAME = """
SELECT id FROM pokemon
WHERE name = %s OR name LIKE CONCAT(%s, '（', '%%')
ORDER BY id
"""


def main() -> None:
    with open(JSON_PATH, encoding="utf-8") as f:
        entries = json.load(f)

    conn = get_conn()
    missed: list[str] = []
    rows: list[dict] = []

    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
            cur.execute("DELETE FROM pokemon_egg_group")

            for item in entries:
                name = (item.get("name") or "").strip()
                groups = item.get("groups") or []
                if not name:
                    continue

                cur.execute(_SQL_IDS_BY_BASE_NAME, (name, name))
                id_rows = cur.fetchall()
                if not id_rows:
                    missed.append(name)
                    continue

                group_names = list(
                    dict.fromkeys(str(x).strip() for x in groups if str(x).strip())
                )
                for row in id_rows:
                    pid = int(row["id"])
                    for g in group_names:
                        rows.append({"pokemon_id": pid, "group_name": g})

            if rows:
                sql = """
                    INSERT INTO pokemon_egg_group (pokemon_id, group_name)
                    VALUES (%(pokemon_id)s, %(group_name)s)
                """
                for i in range(0, len(rows), _BATCH):
                    chunk = rows[i : i + _BATCH]
                    cur.executemany(sql, chunk)

        conn.commit()
    finally:
        conn.close()

    print(f"[import_egg_groups] 写入 {len(rows)} 条关联，JSON 共 {len(entries)} 条")
    if missed:
        print(f"[import_egg_groups] 未在 pokemon 表找到名称（共 {len(missed)} 个）:", file=sys.stderr)
        for n in missed[:50]:
            print(f"  - {n}", file=sys.stderr)
        if len(missed) > 50:
            print(f"  ... 另有 {len(missed) - 50} 个", file=sys.stderr)


if __name__ == "__main__":
    main()
