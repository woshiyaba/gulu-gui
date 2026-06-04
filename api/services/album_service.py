"""精灵相册业务逻辑。

- 新增照片：保存 用户 id / 宠物 id / 图片 URL。
- 设置精选：精选照片在查询时永远排在最前面。
- 查询照片：按 用户 × 宠物 返回，含精选标识。
- 删除照片：先从 OSS 删除对象，再删除数据库记录。
"""

from urllib.parse import urlparse

import anyio

from api.repositories import album_repository
from oss.oss import get_client


def _url_to_key(image_url: str) -> str:
    """从 OSS 访问 URL 还原对象 key（去掉协议 / 域名，保留路径部分）。"""
    path = urlparse(image_url).path
    return path.lstrip("/")


async def add_photo(user_id: int, pet_id: int, image_url: str, is_featured: bool) -> dict:
    return await album_repository.create_photo(user_id, pet_id, image_url, is_featured)


async def list_photos(user_id: int, pet_id: int) -> list[dict]:
    return await album_repository.list_photos(user_id, pet_id)


async def set_featured(photo_id: int, is_featured: bool) -> dict | None:
    return await album_repository.set_featured(photo_id, is_featured)


async def delete_photo(photo_id: int) -> dict | None:
    """删除照片：先删数据库记录拿到 URL，再尽力从 OSS 删除对象。

    OSS 删除失败不阻断（记录已删除），由调用方决定是否容忍残留对象。
    返回被删除的记录；记录不存在时返回 None。
    """
    removed = await album_repository.delete_photo(photo_id)
    if not removed:
        return None

    key = _url_to_key(removed["image_url"])
    if key:
        try:
            client = get_client()
            await anyio.to_thread.run_sync(lambda: client.delete(key))
        except Exception:
            # OSS 删除失败不影响数据库记录已删除的结果，避免脏数据残留在列表中。
            pass

    return removed
