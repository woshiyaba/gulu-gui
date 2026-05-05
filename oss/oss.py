import os
import uuid
from typing import Optional, Union, IO, Any
from urllib.parse import urlparse
import mimetypes
import requests
from dotenv import load_dotenv
from qcloud_cos import CosConfig, CosS3Client


load_dotenv()


class COSClient:
    _client: Optional[CosS3Client] = None

    def __init__(self):
        self.secret_id = os.getenv("COS_SECRET_ID")
        self.secret_key = os.getenv("COS_SECRET_KEY")
        self.region = os.getenv("COS_REGION")
        self.bucket = os.getenv("COS_BUCKET")
        self.domain = os.getenv("COS_DOMAIN")  # 可选：自定义访问域名

        if not all([self.secret_id, self.secret_key, self.region, self.bucket]):
            raise ValueError("请检查 .env 中 COS 配置是否完整")

        if COSClient._client is None:
            config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
                Token=None,
                Scheme="https",
            )
            COSClient._client = CosS3Client(config)

        self.client = COSClient._client

    # ========================
    # 🔧 内部工具方法
    # ========================
    @staticmethod
    def _guess_content_type(filename: str) -> str:
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"

    def _generate_key(self, filename: str, prefix: str = "") -> str:
        ext = os.path.splitext(filename)[-1]
        uid = uuid.uuid4().hex
        key = f"{uid}{ext}"
        if prefix:
            return f"{prefix.strip('/')}/{key}"
        return key

    def _build_url(self, key: str) -> str:
        if self.domain:
            return f"{self.domain.rstrip('/')}/{key}"
        return f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{key}"

    def _put_object(
        self,
        key: str,
        body: Any,
        content_type: Optional[str] = None,
    ) -> None:
        """
        统一封装 put_object：根据 key 自动推断 ContentType，并默认 inline 展示
        """
        if content_type is None:
            content_type = self._guess_content_type(key)

        self.client.put_object(
            Bucket=self.bucket,
            Body=body,
            Key=key,
            ContentType=content_type,
            ContentDisposition="inline",
        )

    # ========================
    # 🚀 上传方法
    # ========================
    def upload_file(
        self,
        file_path: str,
        key: Optional[str] = None,
        prefix: str = "",
    ) -> str:
        """
        上传本地文件
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)

        if not key:
            key = self._generate_key(os.path.basename(file_path), prefix)

        with open(file_path, "rb") as fp:
            self._put_object(key, fp)

        return self._build_url(key)

    def upload_bytes(
        self,
        data: bytes,
        filename: str = "file",
        key: Optional[str] = None,
        prefix: str = "",
    ) -> str:
        """
        上传 bytes（适合接口接收文件）
        """
        if not key:
            key = self._generate_key(filename, prefix)

        self._put_object(key, data)

        return self._build_url(key)

    def upload_fileobj(
        self,
        fileobj: IO,
        filename: str = "file",
        key: Optional[str] = None,
        prefix: str = "",
    ) -> str:
        """
        上传文件流（FastAPI / Flask 的 UploadFile.file）
        """
        if not key:
            key = self._generate_key(filename, prefix)

        self._put_object(key, fileobj)

        return self._build_url(key)

    def upload_from_url(
        self,
        url: str,
        key: Optional[str] = None,
        prefix: str = "",
        timeout: int = 15,
    ) -> str:
        """
        下载远程 URL 的文件，上传到 COS，返回 COS 访问地址
        """
        try:
            resp = requests.get(url, timeout=timeout, stream=True)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"下载远程文件失败: {url}") from exc

        data = resp.content
        if not data:
            raise RuntimeError(f"远程文件为空: {url}")

        remote_content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip()

        if not key:
            filename = os.path.basename(urlparse(url).path) or "file"
            if not os.path.splitext(filename)[-1]:
                ext = mimetypes.guess_extension(remote_content_type) if remote_content_type else ""
                filename = f"{filename}{ext or ''}"
            key = self._generate_key(filename, prefix)

        # 优先用 key 推断；推断不出再回退到远程响应的 Content-Type
        content_type = self._guess_content_type(key)
        if content_type == "application/octet-stream" and remote_content_type:
            content_type = remote_content_type

        self._put_object(key, data, content_type=content_type)

        return self._build_url(key)

    # ========================
    # 🗑 删除
    # ========================
    def delete(self, key: str):
        self.client.delete_object(
            Bucket=self.bucket,
            Key=key,
        )

    # ========================
    # 📥 下载
    # ========================
    def download(self, key: str, save_path: str):
        response = self.client.get_object(
            Bucket=self.bucket,
            Key=key,
        )
        with open(save_path, "wb") as f:
            f.write(response["Body"].get_raw_stream().read())
if __name__ == '__main__':
    cos = COSClient()
    url = cos.upload_from_url("https://rocom.game-walkthrough.com/attrs/guang.webp")
    print(url)
