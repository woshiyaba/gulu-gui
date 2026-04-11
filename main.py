import subprocess
import sys
import time
from pathlib import Path

from db.schema import init_db
from scraper.api_client import fetch_pokemon, fetch_details, fetch_skills
from db.repository import upsert_pokemon, upsert_skills, upsert_details


def _step(msg: str) -> float:
    print(f"\n[>>] {msg} ...", flush=True)
    return time.time()


def _done(start: float, count: int = 0) -> None:
    elapsed = time.time() - start
    suffix = f"（共 {count} 条）" if count else ""
    print(f"    [ok] 完成{suffix}，耗时 {elapsed:.1f}s", flush=True)


_ROOT = Path(__file__).resolve().parent


def _run_py(path: str) -> None:
    subprocess.run([sys.executable, str(_ROOT / path)], cwd=str(_ROOT), check=True)


def main() -> None:
    total_start = time.time()
    print("=" * 50)
    print("  洛克王国精灵图鉴 — 爬取入库")
    print("=" * 50)

    # 1. 建表
    t = _step("初始化数据库表")
    init_db()
    _done(t)

    # 2. 拉取数据
    t = _step("拉取精灵列表 /api/pokemon")
    pokemon_list = fetch_pokemon()
    _done(t, len(pokemon_list))

    t = _step("拉取精灵详情 /api/details")
    details_dict = fetch_details()
    _done(t, len(details_dict))

    t = _step("拉取技能库 /api/skills")
    skills_dict = fetch_skills()
    _done(t, len(skills_dict))

    # 3. 写库
    t = _step("写入 pokemon + pokemon_attribute")
    upsert_pokemon(pokemon_list)
    _done(t, len(pokemon_list))

    t = _step("写入 skill（技能库）")
    upsert_skills(skills_dict)
    _done(t, len(skills_dict))

    t = _step("写入 pokemon_detail + pokemon_skill")
    upsert_details(details_dict)
    _done(t, len(details_dict))

    t = _step("导入蛋孵化数据")
    _run_py("scripts/import_egg_hatch.py")
    _done(t)

    t = _step("导入蛋组（按 name 解析 pokemon.id）")
    _run_py("scripts/import_egg_groups.py")
    _done(t)

    t = _step("更新获取方式")
    _run_py("scripts/update_obtain_method.py")
    _done(t)

    t = _step("导入属性受击倍率矩阵（属性.json）")
    _run_py("scripts/import_attribute_matchups.py")
    _done(t)

    total = time.time() - total_start
    print(f"\n{'=' * 50}")
    print(f"  全部完成！总耗时 {total:.1f}s")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[中止] 用户中断", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] {e}", file=sys.stderr)
        raise
