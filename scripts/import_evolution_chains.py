"""
从 docs/pets/进化.json 导入进化链数据。

JSON 结构：每条 entry 以基础形态为主，evolutionChain 列出该链全部成员（1-3个），
同一链的所有成员共享同一个 chain_id，sort_order 从 1 开始区分顺序。

导入完成后同时更新 pokemon_detail.chain_id，方便直接通过精灵名查完整进化链。

用法：
    uv run python scripts/import_evolution_chains.py
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
    "进化.json",
)

_DDL_EVOLUTION_CHAIN = """
CREATE TABLE IF NOT EXISTS evolution_chain (
    id           INT          NOT NULL AUTO_INCREMENT,
    chain_id     INT          NOT NULL COMMENT '进化链编号，同一链所有成员共享同一值',
    sort_order   TINYINT      NOT NULL COMMENT '在链中的顺序，从 1 开始',
    pokemon_name VARCHAR(50)  NOT NULL COMMENT '基础名，如 板板壳（不含形态后缀）',
    `condition`  VARCHAR(255) NOT NULL DEFAULT '' COMMENT '进化条件描述',
    PRIMARY KEY (id),
    UNIQUE KEY uk_chain_step (chain_id, sort_order),
    KEY idx_pokemon_name (pokemon_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='进化链成员表';
"""

_BATCH = 500


def _ensure_chain_id_column(cur) -> None:
    """旧版 MySQL 不支持 ADD COLUMN IF NOT EXISTS，用 information_schema 判断后按需 ALTER。"""
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'pokemon_detail'
          AND COLUMN_NAME = 'chain_id'
        """
    )
    if cur.fetchone()["cnt"] == 0:
        cur.execute(
            """
            ALTER TABLE pokemon_detail
            ADD COLUMN chain_id INT DEFAULT NULL
            COMMENT '关联 evolution_chain.chain_id'
            """
        )


def _load_chain_rows(entries: list[dict]) -> list[dict]:
    """将 JSON entries 展开为 evolution_chain 行列表，chain_id 从 1 自增。"""
    rows = []
    for chain_id, entry in enumerate(entries, start=1):
        for sort_order, member in enumerate(entry.get("evolutionChain") or [], start=1):
            rows.append(
                {
                    "chain_id": chain_id,
                    "sort_order": sort_order,
                    "pokemon_name": (member.get("name") or "").strip(),
                    "condition": (member.get("condition") or "").strip(),
                }
            )
    return rows


def _insert_chains(cur, rows: list[dict]) -> None:
    """批量插入 evolution_chain 表。"""
    sql = """
        INSERT INTO evolution_chain (chain_id, sort_order, pokemon_name, `condition`)
        VALUES (%(chain_id)s, %(sort_order)s, %(pokemon_name)s, %(condition)s)
    """
    for i in range(0, len(rows), _BATCH):
        cur.executemany(sql, rows[i : i + _BATCH])


def _update_pokemon_detail_chain_ids(cur) -> tuple[int, list[str]]:
    """
    按 evolution_chain.pokemon_name（基础名）模糊匹配 pokemon_detail.pokemon_name，
    将 chain_id 写回 pokemon_detail.chain_id。

    匹配规则（与 import_egg_groups 一致）：
      - 精确匹配：pokemon_detail.pokemon_name = '板板壳'
      - 形态匹配：pokemon_detail.pokemon_name LIKE '板板壳（%'
    同一基础名的所有形态都会获得相同的 chain_id。
    """
    cur.execute("SELECT DISTINCT pokemon_name, chain_id FROM evolution_chain")
    mappings = cur.fetchall()

    updated = 0
    missed: list[str] = []
    for row in mappings:
        base_name = row["pokemon_name"]
        chain_id = row["chain_id"]
        cur.execute(
            """
            UPDATE pokemon_detail
            SET chain_id = %s
            WHERE pokemon_name = %s
               OR pokemon_name LIKE CONCAT(%s, '（', '%%')
            """,
            (chain_id, base_name, base_name),
        )
        if cur.rowcount > 0:
            updated += cur.rowcount
        else:
            missed.append(base_name)

    return updated, missed


def main() -> None:
    with open(JSON_PATH, encoding="utf-8") as f:
        entries = json.load(f)

    chain_rows = _load_chain_rows(entries)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(_DDL_EVOLUTION_CHAIN)
            _ensure_chain_id_column(cur)

            # 清空后重新导入，保证幂等
            cur.execute("DELETE FROM evolution_chain")
            cur.execute("UPDATE pokemon_detail SET chain_id = NULL")

            _insert_chains(cur, chain_rows)
            updated, missed = _update_pokemon_detail_chain_ids(cur)

        conn.commit()
    finally:
        conn.close()

    chain_count = len(entries)
    member_count = len(chain_rows)
    print(
        f"[import_evolution_chains] 导入 {chain_count} 条进化链，"
        f"共 {member_count} 个成员，"
        f"更新 pokemon_detail {updated} 行"
    )
    if missed:
        print(
            f"[import_evolution_chains] 未在 pokemon_detail 表匹配到名称（共 {len(missed)} 个）:",
            file=sys.stderr,
        )
        for name in missed[:50]:
            print(f"  - {name}", file=sys.stderr)
        if len(missed) > 50:
            print(f"  ... 另有 {len(missed) - 50} 个", file=sys.stderr)


if __name__ == "__main__":
    main()
