from fastapi import HTTPException, status

from api.repositories import ops_repository, personality_repository, pokemon_lineup_repository
from api.services.ops_service import ensure_role

LINEUP_TYPE_DICT = "pokemon_lineup_type"

async def _load_valid_stat_keys() -> set[str]:
    rows = await ops_repository.list_dicts_all(dict_type="pokemon_stat")
    return {str(row.get("code", "")).strip() for row in rows if str(row.get("code", "")).strip()}


async def _load_valid_lineup_types() -> set[str]:
    rows = await ops_repository.list_dicts_all(dict_type=LINEUP_TYPE_DICT)
    return {str(row.get("code", "")).strip() for row in rows if str(row.get("code", "")).strip()}


async def _validate_member(member: dict, index: int, valid_stat_keys: set[str]) -> dict:
    if not member.get("pokemon_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 只精灵不能为空")

    stat_keys = [
        (member.get("qual_1") or "").strip(),
        (member.get("qual_2") or "").strip(),
        (member.get("qual_3") or "").strip(),
    ]

    non_empty_stat_keys = [k for k in stat_keys if k]
    for stat_key in non_empty_stat_keys:
        if stat_key not in valid_stat_keys:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 只精灵资质字段不合法")
    if len(non_empty_stat_keys) != len(set(non_empty_stat_keys)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 只精灵资质属性不能重复")

    skill_ids = [member.get("skill_1_id"), member.get("skill_2_id"), member.get("skill_3_id"), member.get("skill_4_id")]
    non_empty_skills = [sid for sid in skill_ids if sid]
    if len(non_empty_skills) != len(set(non_empty_skills)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 只精灵技能不能重复")

    bloodline_dict_id = member.get("bloodline_dict_id")
    if bloodline_dict_id is not None:
        bloodline = await ops_repository.get_dict_by_id(int(bloodline_dict_id))
        if not bloodline or bloodline.get("dict_type") != "pet_bloodline":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 只精灵血脉不存在")

    personality_id = member.get("personality_id")
    if personality_id is not None:
        personality = await personality_repository.get_personality_by_id(int(personality_id))
        if not personality:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"第 {index} 只精灵性格不存在")

    return {
        "pokemon_id": int(member["pokemon_id"]),
        "sort_order": index,
        "bloodline_dict_id": int(bloodline_dict_id) if bloodline_dict_id is not None else None,
        "personality_id": int(personality_id) if personality_id is not None else None,
        "qual_1": stat_keys[0],
        "qual_2": stat_keys[1],
        "qual_3": stat_keys[2],
        "skill_1_id": member.get("skill_1_id"),
        "skill_2_id": member.get("skill_2_id"),
        "skill_3_id": member.get("skill_3_id"),
        "skill_4_id": member.get("skill_4_id"),
        "member_desc": (member.get("member_desc") or "").strip(),
    }


async def _normalize_payload(payload: dict) -> dict:
    members = payload.get("members", [])
    if not members:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="阵容至少需要 1 只精灵")
    if len(members) > 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="阵容最多只能配置 6 只精灵")

    valid_stat_keys = await _load_valid_stat_keys()
    source_type = (payload.get("source_type") or "").strip()
    if source_type:
        valid_lineup_types = await _load_valid_lineup_types()
        if source_type not in valid_lineup_types:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="阵容分类不存在")
    resonance_magic_id = payload.get("resonance_magic_id")
    if resonance_magic_id in ("", 0):
        resonance_magic_id = None
    if resonance_magic_id is not None:
        resonance_magic = await ops_repository.get_resonance_magic_for_ops(int(resonance_magic_id))
        if not resonance_magic:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="共鸣魔法不存在")
    normalized_members: list[dict] = []
    for idx, member in enumerate(members, start=1):
        normalized_members.append(await _validate_member(member, idx, valid_stat_keys))

    return {
        "title": (payload.get("title") or "").strip(),
        "lineup_desc": payload.get("lineup_desc") or "",
        "source_type": source_type,
        "resonance_magic_id": int(resonance_magic_id) if resonance_magic_id is not None else None,
        "sort_order": int(payload.get("sort_order", 1) or 1),
        "is_active": bool(payload.get("is_active", True)),
        "members": normalized_members,
    }


async def list_active_lineups(source_type: str = "") -> list[dict]:
    return await pokemon_lineup_repository.list_active_lineups(source_type=source_type)


async def get_lineup_detail(lineup_id: int) -> dict | None:
    lineup = await pokemon_lineup_repository.get_lineup_by_id(lineup_id)
    if not lineup or not lineup.get("is_active"):
        return None
    return lineup


async def list_lineups_for_ops(
    user: dict,
    keyword: str = "",
    source_type: str = "",
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    total, items = await pokemon_lineup_repository.list_lineups_paginated(
        keyword=keyword,
        source_type=source_type,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_lineup_detail_for_ops(user: dict, lineup_id: int) -> dict:
    ensure_role(user, {"editor", "admin"})
    lineup = await pokemon_lineup_repository.get_lineup_by_id(lineup_id)
    if not lineup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵阵容不存在")
    return lineup


async def create_lineup_for_ops(user: dict, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    normalized = await _normalize_payload(payload)
    item = await pokemon_lineup_repository.create_lineup(normalized)
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_lineup",
        resource_id=str(item["id"]),
        action="create",
        before_json=None,
        after_json=item,
    )
    return item


async def update_lineup_for_ops(user: dict, lineup_id: int, payload: dict) -> dict:
    ensure_role(user, {"editor", "admin"})
    before = await pokemon_lineup_repository.get_lineup_by_id(lineup_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵阵容不存在")
    normalized = await _normalize_payload(payload)
    item = await pokemon_lineup_repository.update_lineup(lineup_id, normalized)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵阵容不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_lineup",
        resource_id=str(lineup_id),
        action="update",
        before_json=before,
        after_json=item,
    )
    return item


async def delete_lineup_for_ops(user: dict, lineup_id: int) -> None:
    ensure_role(user, {"admin"})
    before = await pokemon_lineup_repository.get_lineup_by_id(lineup_id)
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵阵容不存在")
    deleted = await pokemon_lineup_repository.delete_lineup(lineup_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="精灵阵容不存在")
    await ops_repository.create_audit_log(
        user_id=user["id"],
        resource_type="pokemon_lineup",
        resource_id=str(lineup_id),
        action="delete",
        before_json=before,
        after_json=None,
    )


async def search_pokemon_for_ops(user: dict, keyword: str) -> dict:
    ensure_role(user, {"editor", "admin"})
    items = await pokemon_lineup_repository.search_pokemon(keyword.strip())
    return {"items": items}


async def search_skills_for_ops(
    user: dict,
    keyword: str,
    pokemon_id: int | None,
    exclude_skill_ids: list[int] | None = None,
) -> dict:
    ensure_role(user, {"editor", "admin"})
    if not pokemon_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先选择精灵后再搜索技能")
    items = await pokemon_lineup_repository.search_skills(
        keyword=(keyword or "").strip(),
        pokemon_id=int(pokemon_id),
        exclude_skill_ids=exclude_skill_ids or [],
    )
    return {"items": items}
