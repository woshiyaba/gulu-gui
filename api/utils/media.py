from config import BASE_URL

FRIEND_IMAGE_BASE_URL = "http://101.126.137.23/images/friends/"


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
