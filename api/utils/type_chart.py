from __future__ import annotations

from decimal import Decimal
from fractions import Fraction


def _fraction_from_db(value) -> Fraction:
    """把 MySQL DECIMAL / str / float 安全转为 Fraction。"""
    if value is None:
        return Fraction(1, 1)
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        return Fraction(str(value))
    return Fraction(str(value)).limit_denominator(10_000)


def _format_multiplier_label(frac: Fraction) -> str:
    if frac == 0:
        return "0"
    if frac.denominator == 1:
        return str(frac.numerator)
    return f"{frac.numerator}/{frac.denominator}"


def _eff_bucket(frac: Fraction) -> str:
    """前端样式桶：克制(>1) / 一般(1) / 抵抗(<1) / 免疫(0)。"""
    if frac == 0:
        return "immune"
    if frac > 1:
        return "super"
    if frac < 1:
        return "resist"
    return "neutral"


def build_defensive_type_chart_payload(
    defender_attrs: list[str],
    axis: list[str],
    matchup_rows: list[dict],
) -> dict | None:
    """
    根据精灵的 1～2 个属性与单方矩阵，生成「受各进攻属性技能时的倍率」表数据。

    若库中尚未导入 axis（空表），返回 None。
    """
    if not axis:
        return None

    defenders = list(dict.fromkeys([d for d in defender_attrs if d]))
    if not defenders:
        return None

    single: dict[tuple[str, str], Fraction] = {}
    for row in matchup_rows:
        d = row.get("defender_attr")
        a = row.get("attacker_attr")
        if not d or not a:
            continue
        single[(d, a)] = _fraction_from_db(row.get("multiplier"))

    cells: list[dict] = []
    for attacker in axis:
        combined = Fraction(1, 1)
        for d in defenders:
            combined *= single.get((d, attacker), Fraction(1, 1))
        cells.append(
            {
                "attacker_attr": attacker,
                "multiplier": float(combined),
                "label": _format_multiplier_label(combined),
                "bucket": _eff_bucket(combined),
            },
        )

    return {
        "defender_attrs": defenders,
        "cells": cells,
    }
