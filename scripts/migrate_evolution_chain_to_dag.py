"""
进化链全流程迁移（PostgreSQL）：线性 evolution_chain → 边表 pokemon_evolution_chain + chain_id 同步。

连接 config.PG_CONFIG（与 api 异步池、其他 scripts 一致），不使用 MySQL。

步骤（非 --dry-run）：
  1) 解析数据源：evolution_chain（含 pokemon_name）或 evolution_chain_linear_backup
  2) 备份 evolution_chain → evolution_chain_linear_backup（若尚无备份）
  3) 链去重：若多只精灵/多条源链共享同一 pokemon.id，则按连通分量合并，保留分量内最小 chain_id 为主链，丢弃其它源链的线性行；pokemon.chain_id 写回一律用合并后的 id。
  4) DROP CASCADE 并重建 pokemon_evolution_chain：每条链写链首行（pre_pokemon_id=NULL）+ 相邻进化边
  5) 清空本次涉及的 pokemon / pokemon_detail 上旧 chain_id
  6) 确保 pokemon.chain_id 列存在，写回 pokemon 与 pokemon_detail
  7) 校验行数；可选 --archive-linear-source 将 evolution_chain 重命名为归档表

用法：
  uv run python scripts/migrate_evolution_chain_to_dag.py --dry-run
  uv run python scripts/migrate_evolution_chain_to_dag.py
  uv run python scripts/migrate_evolution_chain_to_dag.py --archive-linear-source

依赖：psycopg2-binary（与仓库其他 PG 脚本相同）。规则见 docs/design/pokemon_evolution_chain.md
"""

from __future__ import annotations

import argparse
import sys
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

from config import PG_CONFIG

BACKUP_TABLE = "evolution_chain_linear_backup"
TARGET_TABLE = "pokemon_evolution_chain"
DEFAULT_SOURCE = "evolution_chain"


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def _table_exists(cur, name: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables t
            WHERE t.table_schema = current_schema()
              AND t.table_name = %s
        ) AS ok
        """,
        (name,),
    )
    row = cur.fetchone()
    return bool(row and row.get("ok"))


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns c
            WHERE c.table_schema = current_schema()
              AND c.table_name = %s
              AND c.column_name = %s
        ) AS ok
        """,
        (table, column),
    )
    row = cur.fetchone()
    return bool(row and row.get("ok"))


def _ensure_pokemon_chain_id_column(cur) -> None:
    if _column_exists(cur, "pokemon", "chain_id"):
        return
    print("为 pokemon 表添加 chain_id 列 …")
    cur.execute(
        """
        ALTER TABLE pokemon
        ADD COLUMN chain_id INT NULL
        """
    )
    cur.execute(
        """
        COMMENT ON COLUMN pokemon.chain_id IS
        '关联进化图 chain_id（与 pokemon_evolution_chain 一致）'
        """
    )


def _resolve_pokemon_id(cur, base_name: str) -> int | None:
    base_name = (base_name or "").strip()
    if not base_name:
        return None
    cur.execute("SELECT MIN(id) AS id FROM pokemon WHERE name = %s", (base_name,))
    row = cur.fetchone()
    if row and row.get("id") is not None:
        return int(row["id"])
    like_pat = base_name + "（%"
    cur.execute("SELECT MIN(id) AS id FROM pokemon WHERE name LIKE %s", (like_pat,))
    row = cur.fetchone()
    if row and row.get("id") is not None:
        return int(row["id"])
    return None


def _edge_pre_evolution_condition(pre_row: dict, post_row: dict, *, has_pre_evo_col: bool) -> str:
    if has_pre_evo_col:
        s = (post_row.get("pre_evolution_condition") or "").strip()
        if s:
            return s
    return (pre_row.get("evolution_condition") or "").strip()


def _pick_source_table(cur) -> tuple[str, bool]:
    if _table_exists(cur, DEFAULT_SOURCE) and _column_exists(cur, DEFAULT_SOURCE, "pokemon_name"):
        return DEFAULT_SOURCE, _column_exists(cur, DEFAULT_SOURCE, "pre_evolution_condition")
    if _table_exists(cur, BACKUP_TABLE) and _column_exists(cur, BACKUP_TABLE, "pokemon_name"):
        print(
            f"提示：{DEFAULT_SOURCE} 中无 pokemon_name，改为从 {BACKUP_TABLE} 读取线性数据。"
        )
        return BACKUP_TABLE, _column_exists(cur, BACKUP_TABLE, "pre_evolution_condition")
    raise SystemExit(
        f"找不到可迁移的线性源：需要 {DEFAULT_SOURCE} 或 {BACKUP_TABLE} 中存在列 pokemon_name。"
    )


def _maybe_backup_source(cur, *, source_table: str, dry_run: bool) -> None:
    if dry_run or source_table != DEFAULT_SOURCE:
        return
    if _table_exists(cur, BACKUP_TABLE):
        print(f"[2] 备份表 {BACKUP_TABLE} 已存在，跳过备份。")
        return
    print(f"[2] 备份 {DEFAULT_SOURCE} → {BACKUP_TABLE} …")
    cur.execute(
        f'CREATE TABLE "{BACKUP_TABLE}" AS SELECT * FROM "{DEFAULT_SOURCE}"'
    )


def _recreate_target_table(cur) -> None:
    cur.execute(f'DROP TABLE IF EXISTS "{TARGET_TABLE}" CASCADE')
    cur.execute(
        f"""
        CREATE TABLE "{TARGET_TABLE}" (
            id                      SERIAL PRIMARY KEY,
            chain_id                INT NOT NULL,
            pre_pokemon_id          INT NULL REFERENCES pokemon (id) ON DELETE CASCADE,
            pokemon_id              INT NOT NULL REFERENCES pokemon (id) ON DELETE CASCADE,
            pre_evolution_condition VARCHAR(255) NOT NULL DEFAULT ''
        )
        """
    )
    cur.execute(
        f'COMMENT ON COLUMN "{TARGET_TABLE}".pre_pokemon_id IS '
        f"'NULL 表示链首/无前置；非空表示从该 pokemon 进化到 pokemon_id'"
    )
    cur.execute(
        f"""
        CREATE UNIQUE INDEX uk_pec_edge ON "{TARGET_TABLE}"
            (chain_id, pre_pokemon_id, pokemon_id)
        """
    )
    cur.execute(
        f'CREATE INDEX idx_pec_chain_pre ON "{TARGET_TABLE}" (chain_id, pre_pokemon_id)'
    )
    cur.execute(
        f'CREATE INDEX idx_pec_chain_post ON "{TARGET_TABLE}" (chain_id, pokemon_id)'
    )
    cur.execute(
        f"COMMENT ON TABLE \"{TARGET_TABLE}\" IS '精灵进化有向边（DAG）'"
    )


def _root_pre_evolution_condition(first_row: dict, *, has_pre_evo_col: bool) -> str:
    """链首入图行固定无进化条件。"""
    return ""


def _build_edges(
    cur,
    legacy_rows: list[dict],
    *,
    has_pre_evo: bool,
) -> tuple[list[tuple[int, int | None, int, str]], list[str]]:
    chains: dict[int, list[dict]] = {}
    for r in legacy_rows:
        cid = int(r["chain_id"])
        chains.setdefault(cid, []).append(r)
    for cid in chains:
        chains[cid].sort(key=lambda x: int(x["sort_order"]))

    raw: list[tuple[int, int | None, int, str]] = []
    skipped: list[str] = []

    for chain_id, rows in sorted(chains.items()):
        if not rows:
            continue

        # 链首：无前置 → pre_pokemon_id 存 SQL NULL（Python None），保证整条链在边表中有「根」记录
        first_row = rows[0]
        first_name = (first_row.get("pokemon_name") or "").strip()
        root_id = _resolve_pokemon_id(cur, first_name)
        if root_id is None:
            skipped.append(
                f"chain={chain_id} sort={first_row.get('sort_order')}: "
                f"无法解析链首名 {first_name!r} → pokemon.id"
            )
        else:
            root_cond = _root_pre_evolution_condition(first_row, has_pre_evo_col=has_pre_evo)
            raw.append((chain_id, None, root_id, root_cond))

        for i in range(1, len(rows)):
            pre_row = rows[i - 1]
            post_row = rows[i]
            pre_name = (pre_row.get("pokemon_name") or "").strip()
            post_name = (post_row.get("pokemon_name") or "").strip()
            cond = _edge_pre_evolution_condition(pre_row, post_row, has_pre_evo_col=has_pre_evo)
            if len(cond) > 255:
                cond = cond[:255]

            pre_id = _resolve_pokemon_id(cur, pre_name)
            post_id = _resolve_pokemon_id(cur, post_name)
            if pre_id is None:
                skipped.append(
                    f"chain={chain_id} sort={post_row.get('sort_order')}: "
                    f"无法解析前置名 {pre_name!r} → pokemon.id"
                )
                continue
            if post_id is None:
                skipped.append(
                    f"chain={chain_id} sort={post_row.get('sort_order')}: "
                    f"无法解析后置名 {post_name!r} → pokemon.id"
                )
                continue
            raw.append((chain_id, pre_id, post_id, cond))

    deduped: "OrderedDict[tuple[int, int | None, int], str]" = OrderedDict()
    for chain_id, pre_id, post_id, cond in raw:
        key = (chain_id, pre_id, post_id)
        if key not in deduped:
            deduped[key] = cond
    edges = [(k[0], k[1], k[2], v) for k, v in deduped.items()]
    return edges, skipped


def _insert_edges(cur, edges: list[tuple[int, int | None, int, str]]) -> list[str]:
    if not edges:
        return []
    sql = (
        f'INSERT INTO "{TARGET_TABLE}" '
        "(chain_id, pre_pokemon_id, pokemon_id, pre_evolution_condition) VALUES %s"
    )
    errors: list[str] = []
    try:
        psycopg2.extras.execute_values(
            cur,
            sql,
            edges,
            template="(%s, %s, %s, %s)",
            page_size=500,
        )
    except Exception as bulk_ex:  # noqa: BLE001
        errors.append(f"execute_values 失败，改为逐条: {bulk_ex}")
        row_sql = (
            f'INSERT INTO "{TARGET_TABLE}" '
            "(chain_id, pre_pokemon_id, pokemon_id, pre_evolution_condition) "
            "VALUES (%s, %s, %s, %s)"
        )
        for e in edges:
            try:
                cur.execute(row_sql, e)
            except Exception as ex:  # noqa: BLE001
                errors.append(f"INSERT {e}: {ex}")
    return errors


def _compute_chain_id_merge_map(
    cur,
    legacy_rows: list[dict],
) -> tuple[dict[int, int], list[str]]:
    """
    若同一 pokemon.id 出现在多条源 chain_id 中，则这些 chain_id 视为同一连通分量，
    合并为分量内最小的 chain_id（主链）。返回 merge_map: 原 chain_id -> 主 chain_id。
    """
    all_cids = {int(r["chain_id"]) for r in legacy_rows}
    p2c: dict[int, set[int]] = {}
    for r in legacy_rows:
        cid = int(r["chain_id"])
        pid = _resolve_pokemon_id(cur, (r.get("pokemon_name") or "").strip())
        if pid is None:
            continue
        p2c.setdefault(pid, set()).add(cid)

    adj: dict[int, set[int]] = {c: set() for c in all_cids}
    for cids in p2c.values():
        if len(cids) < 2:
            continue
        cl = sorted(cids)
        for i, a in enumerate(cl):
            for b in cl[i + 1 :]:
                adj[a].add(b)
                adj[b].add(a)

    visited: set[int] = set()
    merge_map: dict[int, int] = {}
    logs: list[str] = []
    for start in sorted(all_cids):
        if start in visited:
            continue
        stack = [start]
        comp: list[int] = []
        visited.add(start)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj.get(u, ()):
                if v not in visited:
                    visited.add(v)
                    stack.append(v)
        m = min(comp)
        for u in comp:
            merge_map[u] = m
        if len(comp) > 1:
            losers = sorted(x for x in comp if x != m)
            logs.append(
                f"链合并：主 chain_id={m}，丢弃源链行 chain_id={losers}（与主链共用精灵）"
            )

    for c in all_cids:
        merge_map.setdefault(c, c)

    return merge_map, logs


def _filter_legacy_rows_for_primary_chains(
    legacy_rows: list[dict],
    merge_map: dict[int, int],
) -> list[dict]:
    """只保留「主链」上的线性行：chain_id 等于其合并分量的最小 id。"""
    return [
        r
        for r in legacy_rows
        if int(r["chain_id"]) == merge_map[int(r["chain_id"])]
    ]


def _remapped_distinct_pairs(
    legacy_rows: list[dict],
    merge_map: dict[int, int],
) -> list[tuple[int, str]]:
    """写回 pokemon / detail 时用合并后的 chain_id；全量源行参与去重。"""
    seen: set[tuple[int, str]] = set()
    out: list[tuple[int, str]] = []
    for r in legacy_rows:
        nm = (r.get("pokemon_name") or "").strip()
        if not nm:
            continue
        cid = merge_map[int(r["chain_id"])]
        key = (cid, nm)
        if key not in seen:
            seen.add(key)
            out.append(key)
    out.sort(key=lambda x: (x[0], x[1]))
    return out


def _clear_chain_ids_for_chains(cur, chain_ids: list[int]) -> tuple[int, int]:
    if not chain_ids:
        return 0, 0
    ph = ", ".join(["%s"] * len(chain_ids))
    pu, du = 0, 0
    if _column_exists(cur, "pokemon", "chain_id"):
        cur.execute(
            f"UPDATE pokemon SET chain_id = NULL WHERE chain_id IN ({ph})",
            chain_ids,
        )
        pu = cur.rowcount
    if _table_exists(cur, "pokemon_detail") and _column_exists(cur, "pokemon_detail", "chain_id"):
        cur.execute(
            f"UPDATE pokemon_detail SET chain_id = NULL WHERE chain_id IN ({ph})",
            chain_ids,
        )
        du = cur.rowcount
    return pu, du


def _sync_pokemon_chain_ids(cur, pairs: list[tuple[int, str]]) -> tuple[int, list[str]]:
    if not _column_exists(cur, "pokemon", "chain_id"):
        return 0, ["pokemon 无 chain_id 列，已跳过归属写入"]
    updated = 0
    missed: list[str] = []
    for chain_id, base_name in pairs:
        like_pat = base_name + "（%"
        cur.execute(
            """
            UPDATE pokemon
            SET chain_id = %s
            WHERE name = %s OR name LIKE %s
            """,
            (chain_id, base_name, like_pat),
        )
        if cur.rowcount > 0:
            updated += cur.rowcount
        else:
            missed.append(f"chain_id={chain_id} pokemon_name={base_name!r}")
    return updated, missed


def _sync_pokemon_detail_chain_ids(cur, pairs: list[tuple[int, str]]) -> tuple[int, list[str]]:
    if not _table_exists(cur, "pokemon_detail") or not _column_exists(
        cur, "pokemon_detail", "chain_id"
    ):
        return 0, []
    updated = 0
    missed: list[str] = []
    for chain_id, base_name in pairs:
        like_pat = base_name + "（%"
        cur.execute(
            """
            UPDATE pokemon_detail
            SET chain_id = %s
            WHERE pokemon_name = %s OR pokemon_name LIKE %s
            """,
            (chain_id, base_name, like_pat),
        )
        if cur.rowcount > 0:
            updated += cur.rowcount
        else:
            missed.append(f"chain_id={chain_id} pokemon_name={base_name!r}")
    return updated, missed


def _verify_counts(cur) -> None:
    cur.execute(f'SELECT COUNT(*) AS c FROM "{TARGET_TABLE}"')
    ec = int(cur.fetchone()["c"])
    print(f"[校验] {TARGET_TABLE} 当前行数: {ec}")
    if _column_exists(cur, "pokemon", "chain_id"):
        cur.execute("SELECT COUNT(*) AS c FROM pokemon WHERE chain_id IS NOT NULL")
        n = int(cur.fetchone()["c"])
        print(f"[校验] pokemon.chain_id 非空行数: {n}")

    cur.execute(
        f"""
        SELECT pokemon_id, COUNT(DISTINCT chain_id) AS chain_cnt
        FROM (
            SELECT chain_id, pokemon_id FROM "{TARGET_TABLE}"
            UNION ALL
            SELECT chain_id, pre_pokemon_id AS pokemon_id
            FROM "{TARGET_TABLE}"
            WHERE pre_pokemon_id IS NOT NULL
        ) x
        GROUP BY pokemon_id
        HAVING COUNT(DISTINCT chain_id) > 1
        """
    )
    bad = cur.fetchall()
    if bad:
        print("[校验] 警告：下列 pokemon.id 仍出现在多个 chain_id 下（数据需人工处理）：")
        for r in bad:
            print(f"       pokemon_id={r['pokemon_id']} chain 数={r['chain_cnt']}")


def _maybe_archive_linear_source(cur, *, archive: bool, source_table: str, dry_run: bool) -> None:
    if dry_run or not archive:
        return
    if source_table != DEFAULT_SOURCE:
        print("[8] 归档跳过：当前数据源不是 evolution_chain。")
        return
    if not _table_exists(cur, DEFAULT_SOURCE):
        print("[8] 归档跳过：evolution_chain 表不存在。")
        return
    suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived = f"evolution_chain_archived_{suffix}"
    print(f'[8] 将 "{DEFAULT_SOURCE}" 重命名为 "{archived}" …')
    cur.execute(f'ALTER TABLE "{DEFAULT_SOURCE}" RENAME TO "{archived}"')
    print(f"     原线性表已归档为 \"{archived}\"；请确认应用已不再依赖旧表名。")


def migrate(*, dry_run: bool = False, archive_linear_source: bool = False) -> None:
    conn = pg_conn()
    conn.autocommit = True
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("[1] 解析数据源 …")
            source_table, has_pre_evo = _pick_source_table(cur)

            select_cols = ["chain_id", "sort_order", "pokemon_name", "evolution_condition"]
            if has_pre_evo:
                select_cols.append("pre_evolution_condition")
            col_sql = ", ".join(select_cols)
            cur.execute(
                f'SELECT {col_sql} FROM "{source_table}" ORDER BY chain_id, sort_order'
            )
            legacy_rows: list[dict] = list(cur.fetchall())
            merge_map, merge_logs = _compute_chain_id_merge_map(cur, legacy_rows)
            legacy_for_edges = _filter_legacy_rows_for_primary_chains(legacy_rows, merge_map)
            pairs = _remapped_distinct_pairs(legacy_rows, merge_map)
            chain_ids = sorted({int(r["chain_id"]) for r in legacy_rows})
            edges, skipped = _build_edges(cur, legacy_for_edges, has_pre_evo=has_pre_evo)

            if dry_run:
                print(f"     源表={source_table}，源行数={len(legacy_rows)}")
                print(
                    f"     主链线性行数={len(legacy_for_edges)}（已按精灵去重合并多余源链）"
                )
                for line in merge_logs:
                    print("     ", line)
                print(
                    f"     写回用 (合并后 chain_id, 名称) 对={len(pairs)}；"
                    f"源 chain_id 种类={len(chain_ids)}"
                )
                print(
                    f"     将写入 {TARGET_TABLE} 行数={len(edges)}，解析跳过={len(skipped)}"
                )
                print(
                    "     非 dry-run 时还将：备份(如需) → 建边表 → 清空并写回 chain_id（PG）。"
                )
                if archive_linear_source:
                    print("     --archive-linear-source：将把 evolution_chain 改名为归档表")
                for line in skipped:
                    print("  ", line)
                return

            _maybe_backup_source(cur, source_table=source_table, dry_run=False)

            print("[3] 链合并（一精灵一条链）：")
            for line in merge_logs:
                print("    ", line)
            if not merge_logs:
                print("     无重叠源链，无需合并。")
            print(
                f"    主链线性行 {len(legacy_for_edges)} / 源行 {len(legacy_rows)}，"
                f"将生成 {TARGET_TABLE} 行 {len(edges)}"
            )

            print(f"[4] 重建并写入 \"{TARGET_TABLE}\" …")
            _recreate_target_table(cur)
            insert_errors = _insert_edges(cur, edges) if edges else []

            cur.execute(f'SELECT COUNT(*) AS c FROM "{TARGET_TABLE}"')
            inserted_rows = int(cur.fetchone()["c"])
            if len(edges) != inserted_rows:
                print(
                    f"[中止] {TARGET_TABLE} 行数 {inserted_rows}，预期 {len(edges)}，"
                    f"不执行 chain_id 清空与写回。"
                )
                for line in insert_errors:
                    print("   ", line)
                return

            print("[5] 清空本次涉及的旧 chain_id（pokemon / pokemon_detail）…")
            cleared_p, cleared_d = _clear_chain_ids_for_chains(cur, chain_ids)
            print(f"     pokemon 清空 {cleared_p} 行，pokemon_detail 清空 {cleared_d} 行")

            print("[6] 写回 pokemon.chain_id …")
            _ensure_pokemon_chain_id_column(cur)
            pu, p_missed = _sync_pokemon_chain_ids(cur, pairs)
            print(f"     pokemon 更新 {pu} 行；未匹配 {len(p_missed)} 个 (chain_id,名称) 对")

            print("[6] 写回 pokemon_detail.chain_id …")
            du, d_missed = _sync_pokemon_detail_chain_ids(cur, pairs)
            print(f"     pokemon_detail 更新 {du} 行；未匹配 {len(d_missed)} 个 (chain_id,名称) 对")

            print("[7] 汇总 …")
            if skipped:
                print(f"     边上解析跳过: {len(skipped)} 条")
                for line in skipped:
                    print("       ", line)
            if insert_errors:
                print(f"     插入告警: {len(insert_errors)} 条")
                for line in insert_errors:
                    print("       ", line)
            if p_missed:
                print(f"     pokemon 未匹配（全量 {len(p_missed)}）:")
                for line in p_missed:
                    print("       ", line)
            if d_missed:
                print(f"     pokemon_detail 未匹配（全量 {len(d_missed)}）:")
                for line in d_missed:
                    print("       ", line)

            _verify_counts(cur)

            _maybe_archive_linear_source(
                cur,
                archive=archive_linear_source,
                source_table=source_table,
                dry_run=False,
            )

            print("全流程迁移执行完毕（PostgreSQL）。")
    finally:
        conn.close()


def main() -> None:
    p = argparse.ArgumentParser(description="进化链线性表 → DAG 边表 + chain_id 同步（PG）")
    p.add_argument("--dry-run", action="store_true", help="只读预览，不写库")
    p.add_argument(
        "--archive-linear-source",
        action="store_true",
        help="成功后把 evolution_chain 改名为 evolution_chain_archived_时间戳",
    )
    args = p.parse_args()
    migrate(dry_run=args.dry_run, archive_linear_source=args.archive_linear_source)


if __name__ == "__main__":
    main()
