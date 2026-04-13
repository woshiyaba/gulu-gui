"""
从 docs/pets/技能石.txt 导入技能石表。

文本格式：
- 每行按空格拆分
- 第一个字段是宠物名
- 后续字段都是技能名

获取方式格式：
    {宠物名}使用{技能名}指定次数(可在游戏图鉴中查看具体次数)

用法：
    uv run python scripts/import_skill_stones.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_conn

TXT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "pets",
    "技能石.txt",
)

DDL = """
CREATE TABLE IF NOT EXISTS skill_stone (
    id            INT          NOT NULL AUTO_INCREMENT,
    skill_name    VARCHAR(50)  NOT NULL COMMENT '技能名称',
    obtain_method VARCHAR(255) NOT NULL DEFAULT '' COMMENT '技能石获取方式',
    PRIMARY KEY (id),
    UNIQUE KEY uk_skill_name (skill_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技能石获取方式表';
"""


def _build_obtain_method(pokemon_name: str, skill_name: str) -> str:
    return f"{pokemon_name} 使用 {skill_name}指定次数(可在游戏图鉴中查看具体次数)"


def _parse_txt(path: str) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    warnings: list[str] = []
    seen_skills: set[str] = set()

    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 2:
                warnings.append(f"[warn] 第 {lineno} 行格式不符，至少要有宠物名和一个技能：{line!r}")
                continue

            pokemon_name = parts[0].strip()
            skill_names = [skill.strip() for skill in parts[1:] if skill.strip()]
            if not pokemon_name or not skill_names:
                warnings.append(f"[warn] 第 {lineno} 行存在空字段，已跳过：{line!r}")
                continue

            for skill_name in skill_names:
                if skill_name in seen_skills:
                    warnings.append(f"[warn] 技能名重复，后续记录已跳过：{skill_name!r}（第 {lineno} 行）")
                    continue

                seen_skills.add(skill_name)
                rows.append(
                    {
                        "skill_name": skill_name,
                        "obtain_method": _build_obtain_method(pokemon_name, skill_name),
                    }
                )

    return rows, warnings


def main() -> None:
    rows, warnings = _parse_txt(TXT_PATH)
    if not rows:
        raise SystemExit("技能石文本未解析到有效数据")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
            cur.execute("DELETE FROM skill_stone")
            cur.executemany(
                """
                INSERT INTO skill_stone (skill_name, obtain_method)
                VALUES (%(skill_name)s, %(obtain_method)s)
                """,
                rows,
            )
        conn.commit()
    finally:
        conn.close()

    print(f"[import_skill_stones] 已写入 {len(rows)} 条技能石记录，来源：{TXT_PATH}")
    for warning in warnings:
        print(warning, file=sys.stderr)


if __name__ == "__main__":
    main()
