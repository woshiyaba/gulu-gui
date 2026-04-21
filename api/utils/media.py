from config import BASE_URL, FRIEND_IMAGE_BASE_URL, SKILL_ICON_BASE_URL, STATIC_BASE_URL


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
    return f"{BASE_URL}{clean_path}"


def build_friend_image_url(image_lc: str, fallback_path: str = "") -> str:
    """优先返回洛克素材朋友图地址，没有 image_lc 时再回退到旧图地址。"""
    if image_lc:
        if image_lc.startswith("http"):
            return image_lc
        return f"{FRIEND_IMAGE_BASE_URL}{image_lc.lstrip('/')}"
    return build_image_url(fallback_path)


def build_skill_icon_url(icon: str) -> str:
    """技能图标 URL：
    - http 开头：原样返回
    - 带路径分隔（老数据，如 "/icon/skill/xxx.png"）：走 build_image_url，拼 BASE_URL
    - 纯文件名（新上传落在 SKILL_ICON_UPLOAD_DIR）：拼 SKILL_ICON_BASE_URL
    """
    if not icon:
        return ""
    if icon.startswith("http"):
        return icon
    if "/" in icon:
        return build_image_url(icon)
    return f"{SKILL_ICON_BASE_URL}{icon}"


def build_yise_image_url(image_yise: str) -> str:
    if not image_yise:
        return ""
    return f"{STATIC_BASE_URL}/images{image_yise}"
