"""
按行读取 docs/宠物地址_1.txt，格式：宠物名|获取方式
将获取方式更新到 pokemon_detail.obtain_method 字段。

用法：
    uv run python scripts/update_obtain_method.py
"""

import sys
import os

# 让脚本从项目根目录导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_conn

TXT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "docs", "获取方式.txt")


def _add_column_if_missing(cur) -> None:
    """若 obtain_method 列不存在，则自动添加。"""
    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'pokemon_detail'
          AND COLUMN_NAME  = 'obtain_method'
    """)
    if cur.fetchone()["cnt"] == 0:
        cur.execute("""
            ALTER TABLE pokemon_detail
            ADD COLUMN obtain_method VARCHAR(255) NOT NULL DEFAULT ''
            COMMENT '宠物获取方式'
        """)
        print("[migrate] 已添加 obtain_method 列")
    else:
        print("[migrate] obtain_method 列已存在，跳过 ALTER")


def _parse_txt(path: str) -> list[tuple[str, str]]:
    """解析文本，返回 [(pokemon_name, obtain_method), ...]，跳过格式不对的行。"""
    records = []
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split("|", 1)
            if len(parts) != 2:
                print(f"[warn] 第 {lineno} 行格式不符，跳过：{line!r}")
                continue
            name, method = parts[0].strip(), parts[1].strip()
            if name and method:
                records.append((name, method))
    return records


def _batch_update(cur, records: list[tuple[str, str]]) -> tuple[int, int]:
    """批量更新（模糊匹配名称），返回 (updated_rows, not_found_count)。"""
    updated_rows = not_found = 0
    # LIKE %name% 可命中名称包含关键字的所有记录，一次 UPDATE 全部写入
    sql = "UPDATE pokemon_detail SET obtain_method = %s WHERE pokemon_name LIKE %s"
    for name, method in records:
        rows_affected = cur.execute(sql, (method, f"%{name}%"))
        if rows_affected:
            updated_rows += rows_affected
        else:
            not_found += 1
            print(f"[warn] 未找到宠物（模糊）：{name!r}")
    return updated_rows, not_found


def main() -> None:
    records = _parse_txt(TXT_PATH)
    print(f"[info] 共解析 {len(records)} 条记录")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            _add_column_if_missing(cur)
            updated_rows, not_found = _batch_update(cur, records)
        conn.commit()
        print(f"[done] 共更新 {updated_rows} 行，未匹配关键字 {not_found} 个")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
