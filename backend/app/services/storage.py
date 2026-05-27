"""MinIO 对象存储服务"""

from io import BytesIO
from pathlib import Path
from typing import Optional

from loguru import logger
from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings

settings = get_settings()


class MinIOStorage:
    """MinIO 对象存储客户端封装"""

    def __init__(self):
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            self._ensure_bucket()
        return self._client

    def _ensure_bucket(self) -> None:
        """确保 bucket 存在"""
        try:
            if not self._client.bucket_exists(settings.MINIO_BUCKET):
                self._client.make_bucket(settings.MINIO_BUCKET)
                logger.info(f"Created MinIO bucket: {settings.MINIO_BUCKET}")
        except S3Error as e:
            logger.error(f"Failed to ensure MinIO bucket: {e}")
            raise

    def upload_file(
        self,
        object_name: str,
        file_path: Optional[str] = None,
        data: Optional[bytes] = None,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        上传文件到 MinIO。
        返回 object_name。
        """
        try:
            if file_path:
                self.client.fput_object(
                    bucket_name=settings.MINIO_BUCKET,
                    object_name=object_name,
                    file_path=file_path,
                    content_type=content_type,
                )
            elif data:
                self.client.put_object(
                    bucket_name=settings.MINIO_BUCKET,
                    object_name=object_name,
                    data=BytesIO(data),
                    length=len(data),
                    content_type=content_type,
                )
            else:
                raise ValueError("Either file_path or data must be provided")

            logger.debug(f"Uploaded to MinIO: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"Failed to upload to MinIO: {e}")
            raise

    def download_file(self, object_name: str) -> bytes:
        """从 MinIO 下载文件"""
        try:
            response = self.client.get_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
            )
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Failed to download from MinIO: {e}")
            raise

    def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """生成预签名 URL（限时访问）"""
        try:
            return self.client.presigned_get_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
                expires=expires_seconds,
            )
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    def delete_file(self, object_name: str) -> None:
        """删除文件"""
        try:
            self.client.remove_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
            )
            logger.debug(f"Deleted from MinIO: {object_name}")
        except S3Error as e:
            logger.error(f"Failed to delete from MinIO: {e}")

    def file_exists(self, object_name: str) -> bool:
        """检查文件是否存在"""
        try:
            self.client.stat_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=object_name,
            )
            return True
        except S3Error:
            return False


# 全局单例
minio_storage = MinIOStorage()
