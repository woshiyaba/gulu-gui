from typing import Optional

import anyio
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from oss.oss import COSClient, get_client

router = APIRouter(prefix="/api/file", tags=["file"])

_cos_client: Optional[COSClient] = None


@router.post("/upload")
async def upload_file(
        file: UploadFile = File(..., description="要上传的文件"),
        prefix: str = Form("", description="可选的对象存储路径前缀，如 images、avatars"),
) -> dict:
    """
    通用文件上传接口：接收前端文件，上传至腾讯云 COS，返回访问 URL。
    """
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传文件为空",
        )

    filename = file.filename or "file"

    try:
        client = get_client()
        url = await anyio.to_thread.run_sync(
            lambda: client.upload_bytes(data, filename=filename, prefix=prefix)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {exc}",
        ) from exc

    return {
        "url": url,
        "filename": filename,
        "size": len(data),
        "content_type": file.content_type,
    }
