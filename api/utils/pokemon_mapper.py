import json

from api.utils.media import build_image_url


def parse_json_list(value) -> list:
    """把数据库里的 JSON 字段安全转成列表。"""
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except Exception:
        return []


def build_attributes(attr_names: str | None, attr_images: str | None) -> list[dict]:
    """把 GROUP_CONCAT 的属性字段还原成前端可直接消费的结构。"""
    names = attr_names.split(",") if attr_names else []
    images = attr_images.split("|||") if attr_images else []
    return [
        {"attr_name": name, "attr_image": build_image_url(image)}
        for name, image in zip(names, images)
    ]


def to_attribute_item(row: dict) -> dict:
    return {
        "attr_name": row["attr_name"],
        "attr_image": build_image_url(row["attr_image"]),
    }


def to_pokemon_list_item(row: dict) -> dict:
    return {
        "no": row["no"],
        "name": row["name"],
        "image_url": build_image_url(row["image"]),
        "type": row["type"],
        "type_name": row["type_name"],
        "form": row["form"],
        "form_name": row["form_name"],
        "attributes": build_attributes(row.get("attr_names"), row.get("attr_images")),
    }


def to_skill_item(row: dict) -> dict:
    return {
        "name": row["name"],
        "attr": row["attr"],
        "power": row["power"],
        "type": row["type"],
        "consume": row["consume"],
        "desc": row["skill_desc"] or "",
        "icon": build_image_url(row["icon"]),
    }


def to_pokemon_detail(base: dict, detail: dict, skills_raw: list[dict]) -> dict:
    """把基础信息、详情、技能拼成详情接口响应。"""
    return {
        "no": base["no"],
        "name": base["name"],
        "image_url": build_image_url(base["image"]),
        "type": base["type"],
        "type_name": base["type_name"],
        "form": base["form"],
        "form_name": base["form_name"],
        "attributes": build_attributes(base.get("attr_names"), base.get("attr_images")),
        "obtain_method": detail.get("obtain_method", ""),
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
            "strong_against": parse_json_list(detail.get("strong_against")),
            "weak_against": parse_json_list(detail.get("weak_against")),
            "resist": parse_json_list(detail.get("resist")),
            "resisted": parse_json_list(detail.get("resisted")),
        },
        "skills": [to_skill_item(skill) for skill in skills_raw],
    }
