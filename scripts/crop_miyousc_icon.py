"""
从 miyousc.cn 拉取雪碧图，按 128px 网格裁出单个图标并上传到 COS。

交互流程：
  1) 输入图片编号 N  → 拉取 https://miyousc.cn/sk/{N}.webp
  2) 循环输入图标索引 → 在内存中裁剪并上传，控制台打印 COS URL
     输入 `new` 切换到另一张大图，输入 `q` 退出

用法：
    uv run python scripts/crop_miyousc_icon.py
"""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
from PIL import Image

from oss.oss import get_client


IMAGE_URL_TEMPLATE = "https://miyousc.cn/sk/{image_id}.webp"
ICON_SIZE = 128
IMAGE_WIDTH = 768
COLUMNS = IMAGE_WIDTH // ICON_SIZE
COS_PREFIX = "skill_icon"


def download_image(image_id: str) -> Image.Image:
    url = IMAGE_URL_TEMPLATE.format(image_id=image_id)
    print(f"[info] 下载 {url}")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content)).convert("RGBA")


def crop_and_upload(image: Image.Image, image_id: str, index: int) -> str:
    row, col = divmod(index, COLUMNS)
    box = (col * ICON_SIZE, row * ICON_SIZE, (col + 1) * ICON_SIZE, (row + 1) * ICON_SIZE)

    if box[2] > image.width or box[3] > image.height:
        raise ValueError(
            f"索引 {index} 超出图片范围 ({image.width}x{image.height})"
        )

    cropped = image.crop(box)
    buf = BytesIO()
    cropped.save(buf, format="PNG")
    buf.seek(0)

    filename = f"{image_id}_{index}.png"
    return get_client().upload_bytes(buf.getvalue(), filename=filename, prefix=COS_PREFIX)


def prompt(message: str) -> str:
    try:
        return input(message).strip()
    except EOFError:
        return "q"


def load_image_interactive() -> tuple[str, Image.Image] | None:
    while True:
        image_id = prompt("输入图片编号 (q 退出): ")
        if image_id.lower() == "q":
            return None
        if not image_id.isdigit():
            print("[warn] 请输入数字编号")
            continue
        try:
            return image_id, download_image(image_id)
        except requests.RequestException as exc:
            print(f"[error] 下载失败: {exc}")


def main() -> int:
    loaded = load_image_interactive()
    if loaded is None:
        return 0
    image_id, image = loaded

    while True:
        text = prompt("输入图标索引 (q 退出 / new 换图): ")
        if not text:
            continue
        lowered = text.lower()
        if lowered == "q":
            return 0
        if lowered == "new":
            loaded = load_image_interactive()
            if loaded is None:
                return 0
            image_id, image = loaded
            continue
        if not text.lstrip("-").isdigit():
            print("[warn] 请输入数字、`new` 或 `q`")
            continue

        index = int(text)
        try:
            url = crop_and_upload(image, image_id, index)
        except ValueError as exc:
            print(f"[warn] {exc}")
            continue
        except Exception as exc:  # COS 上传失败
            print(f"[error] 上传失败: {exc}")
            continue

        print(f"[ok] {index} → {url}")


if __name__ == "__main__":
    sys.exit(main())
