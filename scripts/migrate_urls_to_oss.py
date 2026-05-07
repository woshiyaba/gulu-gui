"""
将 PostgreSQL 中的图片 URL 列批量迁移到自有 OSS（COS）。

流程：
    遍历配置的 (表, 主键, URL 列, 真实 URL 构建器, OSS 前缀)
    -> 用 build_full_url 拼出可下载的真实地址
    -> 走 oss.oss.COSClient.upload_from_url 下载并上传到 COS
    -> 把 COS 返回的 URL 写回原表原列

注意：按需求当前是「全量重新上传」模式 —— 即使列里已经是 OSS 域名，也会再
拉一次重新生成新 key，请勿误跑。脚本会在启动时打印提示，需要 --yes 才会
真正执行写库；不带 --yes 等价 --dry-run。

用法：
    uv run python scripts/migrate_urls_to_oss.py --dry-run
    uv run python scripts/migrate_urls_to_oss.py --scope skill_icon --limit 5 --yes
    uv run python scripts/migrate_urls_to_oss.py --scope pokemon_image,skill_icon --yes
    uv run python scripts/migrate_urls_to_oss.py --scope skill_icon --id 123 --yes
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras

from config import (
    FRIEND_IMAGE_BASE_URL,
    PG_CONFIG,
    RESONANCE_MAGIC_ICON_BASE_URL,
    SKILL_ICON_BASE_URL,
    STATIC_BASE_URL,
)
from oss.oss import COSClient


# ── 历史 URL 构建器（仅本脚本用，用来还原数据库里旧字段对应的真实下载地址）──
# 数据迁移到 OSS 后，业务读路径已不再做任何 URL 拼接；这些函数只在重新跑
# 全量迁移时用来定位老的源 URL。

_BASE_URL = "https://rocom.game-walkthrough.com"


def build_image_url(path: str) -> str:
    """把相对路径拼成完整图片 URL，并去掉文件名中的编号前缀。"""
    if not path:
        return ""
    if path.startswith("http"):
        return path
    dir_part, _, filename = path.rpartition("/")
    if "_" in filename:
        filename = filename.split("_", 1)[1]
    clean_path = f"{dir_part}/{filename}"
    return f"{_BASE_URL}{clean_path}"


def build_friend_image_url(image_lc: str, fallback_path: str = "") -> str:
    if image_lc:
        if image_lc.startswith("http"):
            return image_lc
        return f"{FRIEND_IMAGE_BASE_URL}{image_lc.lstrip('/')}"
    return build_image_url(fallback_path)


def build_skill_icon_url(icon: str) -> str:
    if not icon:
        return ""
    if icon.startswith("http"):
        return icon
    if "/" in icon:
        return build_image_url(icon)
    return f"{SKILL_ICON_BASE_URL}{icon}"


def build_resonance_magic_icon_url(icon: str) -> str:
    if not icon:
        return ""
    if icon.startswith("http"):
        return icon
    if icon.startswith("/resonance-magic/") or icon.startswith("resonance-magic/"):
        _, _, filename = icon.rpartition("/")
        return f"{RESONANCE_MAGIC_ICON_BASE_URL}{filename}"
    if "/" in icon:
        return build_image_url(icon)
    return f"{RESONANCE_MAGIC_ICON_BASE_URL}{icon}"


def build_yise_image_url(image_yise: str) -> str:
    if not image_yise:
        return ""
    return f"{STATIC_BASE_URL}/images{image_yise}"


def _build_egg_url(value: str) -> str:
    if not value:
        return ""
    if value.startswith("http"):
        return value
    return f"{STATIC_BASE_URL}/images/eggs/{value.lstrip('/')}"


def _build_fruit_url(value: str) -> str:
    if not value:
        return ""
    if value.startswith("http"):
        return value
    return f"{STATIC_BASE_URL}/images/fruits/{value.lstrip('/')}"


def _passthrough_or_base(value: str) -> str:
    if not value:
        return ""
    if value.startswith("http"):
        return value
    return build_image_url(value)


@dataclass(frozen=True)
class UrlTarget:
    scope: str
    table: str
    pk: str
    column: str
    build_full_url: Callable[[str], str]
    prefix: str


TARGETS: list[UrlTarget] = [
    UrlTarget("pokemon_image",      "pokemon",         "id", "image",              build_image_url,                  "pokemon/image"),
    UrlTarget("pokemon_image_lc",   "pokemon",         "id", "image_lc",           build_friend_image_url,           "pokemon/image_lc"),
    UrlTarget("pokemon_image_yise", "pokemon",         "id", "image_yise",         build_yise_image_url,             "pokemon/image_yise"),
    UrlTarget("skill_icon",         "skill",           "id", "icon",               build_skill_icon_url,             "skill/icon"),
    UrlTarget("resonance_icon",     "resonance_magic", "id", "icon",               build_resonance_magic_icon_url,   "resonance-magic/icon"),
    UrlTarget("attribute_image",    "attribute",       "id", "image",              build_image_url,                  "attribute/image"),
    UrlTarget("pokemon_mark_image", "pokemon_mark",    "id", "image",              build_image_url,                  "pokemon-mark/image"),
    UrlTarget("pokemon_egg_icon",   "pokemon_egg",     "id", "icon",               _build_egg_url,                   "pokemon-egg/icon"),
    UrlTarget("pokemon_fruit_icon", "pokemon_fruit",   "id", "icon",               _build_fruit_url,                 "pokemon-fruit/icon"),
    UrlTarget("category_image",     "category",        "id", "category_image_url", _passthrough_or_base,             "category/image"),
    UrlTarget("banner_image",       "banner",          "id", "image_url",          _passthrough_or_base,             "banner/image"),
]

TARGETS_BY_SCOPE: dict[str, UrlTarget] = {t.scope: t for t in TARGETS}


def pg_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["dbname"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )


def _step(msg: str) -> float:
    print(f"\n[>>] {msg} ...", flush=True)
    return time.time()


def _done(stats: dict, start: float) -> None:
    elapsed = time.time() - start
    print(
        f"    [ok] processed={stats['processed']} updated={stats['updated']} "
        f"skip_empty={stats['skip_empty']} fail={stats['fail']} "
        f"({elapsed:.2f}s)",
        flush=True,
    )


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
          AND column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def _process_target(
    target: UrlTarget,
    cos: COSClient,
    args: argparse.Namespace,
    failures_writer: csv.writer,
) -> dict:
    stats = {"processed": 0, "updated": 0, "skip_empty": 0, "fail": 0}
    start = _step(f"scope={target.scope} {target.table}.{target.column}")

    conn = pg_conn()
    conn.autocommit = False
    try:
        cur = conn.cursor()

        if not _column_exists(cur, target.table, target.column):
            print(
                f"    [warn] {target.table}.{target.column} 不存在，跳过该 scope",
                flush=True,
            )
            return stats

        sql = (
            f"SELECT {target.pk}, {target.column} FROM {target.table} "
            f"WHERE {target.column} IS NOT NULL AND {target.column} <> ''"
        )
        params: list = []
        if args.id is not None:
            sql += f" AND {target.pk} = %s"
            params.append(args.id)
        sql += f" ORDER BY {target.pk}"
        if args.limit:
            sql += " LIMIT %s"
            params.append(args.limit)

        cur.execute(sql, params)
        rows = cur.fetchall()
        total = len(rows)
        print(f"    选中 {total} 行", flush=True)

        for idx, (pk, raw) in enumerate(rows, start=1):
            stats["processed"] += 1
            src_url = target.build_full_url(raw)
            if not src_url:
                stats["skip_empty"] += 1
                continue

            if args.dry_run:
                print(
                    f"    [dry-run] {target.scope} pk={pk} raw={raw!r} -> src={src_url}",
                    flush=True,
                )
                continue

            try:
                oss_url = cos.upload_from_url(src_url, prefix=target.prefix)
            except Exception as exc:
                stats["fail"] += 1
                failures_writer.writerow(
                    [target.scope, pk, raw, src_url, repr(exc)]
                )
                print(
                    f"    [fail] {target.scope} pk={pk} src={src_url} err={exc}",
                    flush=True,
                )
                continue

            cur.execute(
                f"UPDATE {target.table} SET {target.column} = %s WHERE {target.pk} = %s",
                (oss_url, pk),
            )
            stats["updated"] += 1

            if idx % 50 == 0 or idx == total:
                print(
                    f"    [progress] {target.scope} {idx}/{total} "
                    f"updated={stats['updated']} fail={stats['fail']}",
                    flush=True,
                )

        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    _done(stats, start)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="批量把 PG 图片 URL 迁移到 OSS")
    parser.add_argument(
        "--scope",
        default="",
        help=f"逗号分隔的 scope 子集，留空=全部。可选: {', '.join(TARGETS_BY_SCOPE)}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要做什么，不下载、不上传、不写库",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="确认进行真实写库；未带 --yes 则等价 --dry-run",
    )
    parser.add_argument("--limit", type=int, default=0, help="每个 scope 最多处理 N 行")
    parser.add_argument("--id", type=int, default=None, help="只处理指定主键")
    args = parser.parse_args()

    if not args.yes and not args.dry_run:
        print(
            "[hint] 未带 --yes 且未带 --dry-run，自动进入 dry-run 模式以防误跑。",
            flush=True,
        )
        args.dry_run = True

    if args.scope:
        scopes = [s.strip() for s in args.scope.split(",") if s.strip()]
        unknown = [s for s in scopes if s not in TARGETS_BY_SCOPE]
        if unknown:
            print(f"[error] 未知 scope: {unknown}", flush=True)
            sys.exit(1)
        targets = [TARGETS_BY_SCOPE[s] for s in scopes]
    else:
        targets = list(TARGETS)

    print(
        f"[info] mode={'dry-run' if args.dry_run else 'WRITE'} "
        f"scopes={[t.scope for t in targets]} limit={args.limit or 'ALL'} id={args.id}",
        flush=True,
    )

    cos = COSClient() if not args.dry_run else None  # dry-run 不实例化 COS

    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fail_path = log_dir / f"migrate_urls_to_oss_failures_{ts}.csv"

    overall = {"processed": 0, "updated": 0, "skip_empty": 0, "fail": 0}
    with open(fail_path, "w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["scope", "pk", "raw_value", "src_url", "error"])

        for target in targets:
            stats = _process_target(target, cos, args, writer)
            for k, v in stats.items():
                overall[k] += v

    print(
        "\n[summary] "
        f"processed={overall['processed']} updated={overall['updated']} "
        f"skip_empty={overall['skip_empty']} fail={overall['fail']} "
        f"dry_run={args.dry_run}",
        flush=True,
    )
    if overall["fail"]:
        print(f"[summary] 失败明细 -> {fail_path}", flush=True)
    else:
        # 没有失败时清理空文件
        try:
            os.remove(fail_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
