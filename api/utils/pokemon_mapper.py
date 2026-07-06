def parse_egg_groups(egg_group_names: str | None) -> list[str]:
    """把标量子查询 GROUP_CONCAT 的蛋组字段还原成列表。"""
    if not egg_group_names:
        return []
    return [x.strip() for x in egg_group_names.split(",") if x.strip()]


def build_attributes(attr_names: str | None, attr_images: str | None) -> list[dict]:
    """把 GROUP_CONCAT 的属性字段还原成前端可直接消费的结构。"""
    names = attr_names.split(",") if attr_names else []
    images = attr_images.split("|||") if attr_images else []
    return [
        {"attr_name": name, "attr_image": image or ""}
        for name, image in zip(names, images)
    ]


def to_attribute_item(row: dict) -> dict:
    return {
        "attr_name": row["attr_name"],
        "attr_image": row.get("attr_image") or "",
    }


def to_pokemon_list_item(row: dict) -> dict:
    return {
        "id": row["id"],
        "no": row["no"],
        "name": row["name"],
        "image_url": row.get("image_lc") or row.get("image") or "",
        "image_yise_url": row.get("image_yise") or "",
        "type": row["type"],
        "type_name": row["type_name"],
        "form": row["form"],
        "form_name": row["form_name"],
        "attributes": build_attributes(row.get("attr_names"), row.get("attr_images")),
        "egg_groups": parse_egg_groups(row.get("egg_group_names")),
    }


def to_skill_item(row: dict) -> dict:
    return {
        "name": row["name"],
        "attr": row["attr"],
        "power": row["power"],
        "type": row["type"],
        "source": row.get("source", ""),
        "consume": row["consume"],
        "desc": row["skill_desc"] or "",
        "icon": row.get("icon") or "",
    }


def _to_egg_hatch_info(row: dict | None) -> dict | None:
    """把 egg_hatch_pet 行转成前端可消费的 dict。"""
    if not row:
        return None
    height_low = row.get("height_low", 0) or 0
    height_high = row.get("height_high", 0) or 0
    weight_low = row.get("weight_low", 0) or 0
    weight_high = row.get("weight_high", 0) or 0
    # 没有任何有效的体型区间数据，当作无孵蛋信息处理
    if not (height_low or height_high or weight_low or weight_high):
        return None
    return {
        "height_low": height_low,
        "height_high": height_high,
        "weight_low": weight_low,
        "weight_high": weight_high,
        "big_size_length": row.get("big_size_length_min", 0) or 0,
        "big_size_weight": row.get("big_size_weight_min", 0) or 0,
        "small_size_length": row.get("small_size_length_max", 0) or 0,
        "small_size_weight": row.get("small_size_weight_max", 0) or 0,
    }


def to_pokemon_detail(base: dict, detail: dict, skills_raw: list[dict], egg_hatch: dict | None = None) -> dict:
    """把基础信息、详情、技能拼成详情接口响应。"""
    return {
        "id": base["id"],
        "no": base["no"],
        "name": base["name"],
        "image_url": base.get("image_lc") or base.get("image") or "",
        "image_yise_url": base.get("image_yise") or "",
        "type": base["type"],
        "type_name": base["type_name"],
        "form": base["form"],
        "form_name": base["form_name"],
        "attributes": build_attributes(base.get("attr_names"), base.get("attr_images")),
        "egg_groups": parse_egg_groups(base.get("egg_group_names")),
        "obtain_method": detail.get("obtain_method", ""),
        "desc": detail.get("desc") or "",
        "stats": {
            "hp": detail.get("hp", 0),
            "atk": detail.get("atk", 0),
            "matk": detail.get("matk", 0),
            "def_val": detail.get("def_val", 0),
            "mdef": detail.get("mdef", 0),
            "spd": detail.get("spd", 0),
        },
        "trait": {
            "name": detail.get("trait_name", ""),
            "desc": detail.get("trait_desc", ""),
        },
        "restrain": {
            "strong_against": [],
            "weak_against": [],
            "resist": [],
            "resisted": [],
        },
        "skills": [to_skill_item(skill) for skill in skills_raw],
        "egg_hatch_info": _to_egg_hatch_info(egg_hatch),
    }
