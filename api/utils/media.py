from config import BASE_URL


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
