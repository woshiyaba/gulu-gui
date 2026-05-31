#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""根据 docs/egg/egg.js 中写死的体型数据更新 egg_hatch_pet 表。

逻辑：
1. 解析 docs/egg/egg.js（CommonJS 模块）中的 spirits 数组。
2. 仅处理同时拥有 bigSizeLengthMin / bigSizeWeightMin /
   smallSizeLengthMax / smallSizeWeightMax 四个字段的精灵。
3. 把 no 拼接成 "NO.017" 这种格式（NO. + 3 位补零）。
4. 用该编号去 pokemon 表查询对应的宠物 id（一个编号可能对应多条，逐条处理）。
5. 用 pokemon_id 把上述四个字段更新到 egg_hatch_pet 表。
   egg.js 中长度单位是米、重量单位是千克；与 egg_hatch_pet 现有的
   height/weight 列保持一致，长度 ×100 存厘米、重量 ×1000 存克，四舍五入取整。

默认是 **演练(dry-run)** 模式，只打印将要执行的更新，不写库。
确认无误后加 --commit 才会真正写入。

用法：
    uv run python scripts/update_egg_hatch_pet.py            # 演练，不写库
    uv run python scripts/update_egg_hatch_pet.py --commit   # 真正写入
"""

import argparse
import os
import re
import sys

import psycopg2

# 让脚本能 import 根目录的 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

# pokemon 表中存放 "NO.017" 这种编号的列
NO_COLUMN = "no"

# egg.js 字段 -> (egg_hatch_pet 列名, 入库时的换算系数)
# 长度 米 -> 厘米 (×100)，重量 千克 -> 克 (×1000)
FIELD_MAP = [
    ("bigSizeLengthMin", "big_size_length_min", 100),
    ("bigSizeWeightMin", "big_size_weight_min", 1000),
    ("smallSizeLengthMax", "small_size_length_max", 100),
    ("smallSizeWeightMax", "small_size_weight_max", 1000),
]

REQUIRED_FIELDS = [f for f, _, _ in FIELD_MAP]

EGG_JS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "egg", "egg.js",
)


def parse_egg_js(path):
    """从 egg.js 中提取每个精灵的 no 以及四个体型字段。

    egg.js 不是合法 JSON（无引号 key、形如 .28 的数值），这里用正则按对象
    分块提取所需字段，避免引入额外解析依赖。
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    results = []
    # spirits 数组里每个对象之间以 "}, {" 分隔
    chunks = re.split(r"\}\s*,\s*\{", text)
    for chunk in chunks:
        m_no = re.search(r"\bno:\s*(\d+)", chunk)
        if not m_no:
            continue

        data = {}
        for field in REQUIRED_FIELDS:
            m = re.search(rf"\b{field}:\s*(-?[\d.]+)", chunk)
            if m:
                data[field] = float(m.group(1))

        # 只处理四个字段齐全的精灵
        if all(field in data for field in REQUIRED_FIELDS):
            results.append((int(m_no.group(1)), data))

    return results


def format_no(no):
    """11 -> 'NO.011'，375 -> 'NO.375'。"""
    return "NO.%03d" % no


def main():
    parser = argparse.ArgumentParser(description="更新 egg_hatch_pet 表的体型数据")
    parser.add_argument(
        "--commit",
        action="store_true",
        help="真正写入数据库（默认仅演练打印）",
    )
    parser.add_argument(
        "--egg-js",
        default=EGG_JS_PATH,
        help="egg.js 文件路径（默认 docs/egg/egg.js）",
    )
    args = parser.parse_args()

    spirits = parse_egg_js(args.egg_js)
    print(f"从 {args.egg_js} 解析出 {len(spirits)} 条带体型字段的精灵\n")
    if not spirits:
        return

    columns = [col for _, col, _ in FIELD_MAP]
    set_clause = ", ".join(f"{col} = %s" for col in columns)
    update_sql = f"UPDATE egg_hatch_pet SET {set_clause} WHERE pokemon_id = %s"
    select_sql = f"SELECT id FROM pokemon WHERE {NO_COLUMN} = %s"

    conn = psycopg2.connect(**config.PG_CONFIG)
    try:
        total_updated = 0
        no_pokemon = []      # pokemon 表查不到的编号
        no_egg_row = []      # 有 pokemon 但 egg_hatch_pet 无对应行
        with conn.cursor() as cur:
            for no, data in spirits:
                no_str = format_no(no)
                cur.execute(select_sql, (no_str,))
                pokemon_ids = [row[0] for row in cur.fetchall()]
                if not pokemon_ids:
                    no_pokemon.append(no_str)
                    print(f"[未找到] {no_str} 在 pokemon 表中没有对应记录")
                    continue

                # 米->厘米、千克->克，四舍五入取整
                values = [round(data[field] * factor) for field, _, factor in FIELD_MAP]

                for pid in pokemon_ids:
                    print(
                        f"[更新] {no_str} -> pokemon_id={pid} | "
                        + ", ".join(f"{col}={val}" for col, val in zip(columns, values))
                    )
                    if args.commit:
                        cur.execute(update_sql, values + [pid])
                        if cur.rowcount == 0:
                            no_egg_row.append(f"{no_str}(pid={pid})")
                            print(
                                f"    [警告] pokemon_id={pid} 在 egg_hatch_pet 无记录，未更新"
                            )
                        else:
                            total_updated += cur.rowcount

        if args.commit:
            conn.commit()
            print(f"\n已提交，共更新 {total_updated} 条 egg_hatch_pet 记录。")
        else:
            print("\n演练完成（未写库）。确认无误后加 --commit 真正写入。")

        if no_pokemon:
            print(f"\npokemon 表中未找到的编号（{len(no_pokemon)} 个）：")
            print("  " + ", ".join(no_pokemon))
        if no_egg_row:
            print(f"\negg_hatch_pet 中无对应行、未能更新（{len(no_egg_row)} 个）：")
            print("  " + ", ".join(no_egg_row))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
