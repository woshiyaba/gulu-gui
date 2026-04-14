"""
从 TSV 文件读取分类映射，并按 category_id 回写 category 表的 type/description。

文件格式（使用 \t 分隔）：
    第一列: type
    第二列: description
    第三列: category_id
    其余列: 可忽略

用法：
    uv run python scripts/update_category_from_tsv.py
    uv run python scripts/update_category_from_tsv.py --dry-run
    uv run python scripts/update_category_from_tsv.py --file docs/pets/category_map.txt
"""

import argparse
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_conn

DEFAULT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "pets",
    "category_map.txt",
)


def _parse_tsv(file_path: str) -> list[dict[str, Any]]:
    """解析 TSV，每行只读取前 3 列。"""
    records: list[dict[str, Any]] = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 3:
                raise ValueError(f"第 {line_no} 行列数不足 3 列: {line}")

            type_value = parts[0].strip()
            description = parts[1].strip()
            category_id_text = parts[2].strip()

            if not category_id_text:
                raise ValueError(f"第 {line_no} 行 category_id 为空")

            try:
                category_id = int(category_id_text)
            except ValueError as exc:
                raise ValueError(
                    f"第 {line_no} 行 category_id 不是整数: {category_id_text}"
                ) from exc

            records.append(
                {
                    "line_no": line_no,
                    "category_id": category_id,
                    "type": type_value,
                    "description": description,
                }
            )

    if not records:
        raise ValueError("未解析到任何有效数据")

    return records


def _deduplicate_by_category_id(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    category_id 去重：同一个 category_id 如果出现多次，保留最后一条。
    这样与人工维护表格时“后写覆盖前写”的直觉一致。
    """
    latest_by_id: dict[int, dict[str, Any]] = {}
    for row in records:
        latest_by_id[row["category_id"]] = row
    return list(latest_by_id.values())


def _update_category(rows: list[dict[str, Any]], dry_run: bool) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            sql = """
                UPDATE category
                SET type = %(type)s,
                    description = %(description)s
                WHERE category_id = %(category_id)s
            """
            matched = 0
            changed = 0

            for row in rows:
                cur.execute(sql, row)
                matched += cur.rowcount
                if cur.rowcount > 0:
                    changed += 1

            if dry_run:
                conn.rollback()
                print(f"[dry-run] 已解析 {len(rows)} 条，命中并尝试更新 {changed} 条，已回滚")
            else:
                conn.commit()
                print(f"[done] 已解析 {len(rows)} 条，成功更新 {changed} 条")

            missing = len(rows) - changed
            if missing > 0:
                print(f"[warn] 有 {missing} 条 category_id 在 category 表中未匹配到")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="解析 TSV 并按 category_id 更新 category.type/description"
    )
    parser.add_argument(
        "--file",
        default=DEFAULT_FILE,
        help="TSV 文件路径，默认 docs/pets/category_map.txt",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只执行更新演练并回滚，不真正写库",
    )
    args = parser.parse_args()

    rows = _parse_tsv(args.file)
    rows = _deduplicate_by_category_id(rows)
    _update_category(rows, args.dry_run)


if __name__ == "__main__":
    main()
