import json
from pathlib import Path

from fastapi import HTTPException, status

from api.repositories import ops_repository, personality_repository
from api.services.ops_service import ensure_role

ALLOWED_MODS = {-0.10, 0.00, 0.10}
STAT_KEYS = ("hp", "phy_atk", "mag_atk", "phy_def", "mag_def", "spd")
STAT_KEY_TO_COL = personality_repository.STAT_KEY_TO_COL
COL_TO_STAT_KEY = {v: k for k, v in STAT_KEY_TO_COL.items()}

PERSONALITY_JSON_PATH = (
    Path(__file__).resolve().parent.parent.parent / "docs" / "pets" / "personalities.json"
)


def _float_row(row: dict) -> dict:
    """把 psycopg 返回的 Decimal 转成 float，便于 pydantic 序列化。"""
    if row is None:
        return row
    out = dict(row)
    for col in personality_repository.STAT_COLS:
        if col in out and out[col] is not None:
            out[col] = float(out[col])
    return out


def _derive_flags(row: dict) -> dict:
    """根据六维修正推断 buff_stat / nerf_stat / is_neutral。"""
    if row is None:
        return row
    out = dict(row)
    buff_stat: str | None = None
    nerf_stat: str | None = None
    for col in personality_repository.STAT_COLS:
        val = out.get(col)
        if val is None:
            continue
        v = float(val)
        if v > 0 and buff_stat is None:
            buff_stat = COL_TO_STAT_KEY[col]
        elif v < 0 and nerf_stat is None:
            nerf_stat = COL_TO_STAT_KEY[col]
    out["buff_stat"] = buff_stat
    out["nerf_stat"] = nerf_stat
    out["is_neutral"] = buff_stat is None and nerf_stat is None
    return out


def _serialize(row: dict | None) -> dict | None:
    if row is None:
        return None
    return _derive_flags(_float_row(row))


def _validate_payload(payload: dict) -> None:
    name_en = (payload.get("name_en") or "").strip()
    name_zh = (payload.get("name_zh") or "").strip()
    if not name_en:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="英文名不能为空")
    if len(name_en) > 32:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="英文名最长 32 个字符")
    if not name_zh:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="中文名不能为空")
    if len(name_zh) > 16:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="中文名最长 16 个字符")
    payload["name_en"] = name_en
    payload["name_zh"] = name_zh

    for col in personality_repository.STAT_COLS:
        val = float(payload.get(col) or 0)
        if round(val, 2) not in {round(x, 2) for x in ALLOWED_MODS}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{col} 取值必须是 -0.10 / 0 / 0.10",
            )
        payload[col] = round(val, 2)

    # 可选：强校验一加一减一中性
    buff = sum(1 for c in personality_repository.STAT_COLS if payload[c] == 0.10)
    nerf = sum(1 for c in personality_repository.STAT_COLS if payload[c] == -0.10)
    if not ((buff == 0 and nerf == 0) or (buff == 1 and nerf == 1)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="性格修正必须满足：恰好一项 +10% + 一项 -10%，其余为 0；或全部为 0。",
        )


# ── 公共只读 ────────────────────────────────────────────────

async def list_personalities_public() -> list[dict]:
    _, items = await personality_repository.list_personalities(page=1, page_size=100)
    return [_serialize(r) for r in items]


# ── Ops 后台 ────────────────────────────────────────────────

async def list_personalities_for_ops(
    user: dict,
    keyword: str = "",
    buff_stat: str = "",
    nerf_stat: str = "",
    page: int = 1,
    page_size: int = 100,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    total, items = await personality_repository.list_personalities(
        keyword=keyword,
        buff_stat=buff_stat,
        nerf_stat=nerf_stat,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize(r) for r in items],
    }


async def get_personality_for_ops(user: dict, pid: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    row = await personality_repository.get_personality_by_id(pid)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="性格不存在")
    return _serialize(row)


async def create_personality_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"admin"})
    _validate_payload(payload)
    if payload.get("id") is None:
        payload["id"] = await personality_repository.next_available_id()
    else:
        pid = int(payload["id"])
        if pid < 1 or pid > 999:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="id 必须在 1-999 之间")
        if await personality_repository.id_exists(pid):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"id={pid} 已存在")
        payload["id"] = pid

    try:
        row = await personality_repository.create_personality(payload)
    except Exception as exc:  # UniqueViolation 等
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"创建失败：{exc}") from exc

    item = _serialize(row)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="personality",
        resource_id=str(item["id"]),
        action="create",
        before_json=None,
        after_json=item,
    )
    return item


async def update_personality_for_ops(user: dict, pid: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await personality_repository.get_personality_by_id(pid)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="性格不存在")
    _validate_payload(payload)
    try:
        row = await personality_repository.update_personality(pid, payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"更新失败：{exc}") from exc

    item = _serialize(row)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="personality",
        resource_id=str(pid),
        action="update",
        before_json=_serialize(before),
        after_json=item,
    )
    return item


async def delete_personality_for_ops(user: dict, pid: int) -> None:
    ensure_role(user, {"admin"})
    before = await personality_repository.get_personality_by_id(pid)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="性格不存在")
    deleted = await personality_repository.delete_personality(pid)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="性格不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="personality",
        resource_id=str(pid),
        action="delete",
        before_json=_serialize(before),
        after_json=None,
    )


async def reset_personalities_from_json(user: dict) -> dict:
    """从 docs/pets/personalities.json 全量重建（仅 admin）。"""
    ensure_role(user, {"admin"})
    if not PERSONALITY_JSON_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"未找到数据源文件：{PERSONALITY_JSON_PATH}",
        )
    with open(PERSONALITY_JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    rows: list[dict] = []
    for item in data:
        rows.append({
            "id": int(item["id"]),
            "name_en": item["name"],
            "name_zh": item["localized"]["zh"],
            "hp_mod_pct": float(item.get("hp_mod_pct", 0) or 0),
            "phy_atk_mod_pct": float(item.get("phy_atk_mod_pct", 0) or 0),
            "mag_atk_mod_pct": float(item.get("mag_atk_mod_pct", 0) or 0),
            "phy_def_mod_pct": float(item.get("phy_def_mod_pct", 0) or 0),
            "mag_def_mod_pct": float(item.get("mag_def_mod_pct", 0) or 0),
            "spd_mod_pct": float(item.get("spd_mod_pct", 0) or 0),
        })

    inserted = await personality_repository.bulk_upsert_personalities(rows)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="personality",
        resource_id="*",
        action="reset",
        before_json=None,
        after_json={"inserted": inserted, "source": "json"},
    )
    return {"inserted": inserted, "source": "json"}
