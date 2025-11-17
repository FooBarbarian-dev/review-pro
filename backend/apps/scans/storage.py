"""
S3/MinIO storage integration for SARIF files (ADR-005).

Implements hybrid storage strategy:
- Full SARIF files stored in S3/MinIO
- Normalized findings stored in PostgreSQL
"""
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.client import Config
from django.conf import settings
from typing import Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


class SARIFStorage:
    """
    Handle SARIF file storage in S3/MinIO.

    Provides upload, download, and presigned URL generation.
    """

    def __init__(self):
        """Initialize S3/MinIO client."""
        if not settings.USE_S3:
            logger.warning("S3 storage is disabled in settings")

        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
                config=Config(signature_version='s3v4')
            )
            self.bucket = settings.SARIF_BUCKET_NAME

            # Ensure bucket exists
            self._ensure_bucket_exists()

        except NoCredentialsError:
            logger.error("S3 credentials not found")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            logger.debug(f"Bucket {self.bucket} exists")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                # Bucket doesn't exist, create it
                logger.info(f"Creating bucket {self.bucket}")
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket)
                    logger.info(f"Bucket {self.bucket} created successfully")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket: {e}")
                raise

    def upload_sarif(
        self,
        scan_id: str,
        sarif_content: str,
        organization_id: str,
        repository_id: str
    ) -> Tuple[str, int]:
        """
        Upload SARIF file to S3/MinIO.

        Args:
            scan_id: UUID of the scan
            sarif_content: SARIF JSON content as string
            organization_id: UUID of organization
            repository_id: UUID of repository

        Returns:
            Tuple of (s3_path, file_size_bytes)

        Raises:
            ClientError: If upload fails
        """
        # Generate S3 path with organization hierarchy
        # Format: org_id/repo_id/scans/scan_id.sarif
        s3_key = f"{organization_id}/{repository_id}/scans/{scan_id}.sarif"

        try:
            # Convert string to bytes
            sarif_bytes = sarif_content.encode('utf-8')
            file_size = len(sarif_bytes)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=sarif_bytes,
                ContentType='application/sarif+json',
                Metadata={
                    'scan_id': scan_id,
                    'organization_id': organization_id,
                    'repository_id': repository_id
                }
            )

            logger.info(f"Uploaded SARIF file to {s3_key} ({file_size} bytes)")
            return s3_key, file_size

        except ClientError as e:
            logger.error(f"Failed to upload SARIF file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading SARIF: {e}")
            raise

    def upload_sarif_file(
        self,
        scan_id: str,
        file_path: str,
        organization_id: str,
        repository_id: str
    ) -> Tuple[str, int]:
        """
        Upload SARIF file from filesystem to S3/MinIO.

        Args:
            scan_id: UUID of the scan
            file_path: Path to SARIF file on disk
            organization_id: UUID of organization
            repository_id: UUID of repository

        Returns:
            Tuple of (s3_path, file_size_bytes)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sarif_content = f.read()

            return self.upload_sarif(
                scan_id=scan_id,
                sarif_content=sarif_content,
                organization_id=organization_id,
                repository_id=repository_id
            )

        except FileNotFoundError:
            logger.error(f"SARIF file not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to read SARIF file {file_path}: {e}")
            raise

    def download_sarif(self, s3_key: str) -> str:
        """
        Download SARIF file from S3/MinIO.

        Args:
            s3_key: S3 object key

        Returns:
            SARIF content as string

        Raises:
            ClientError: If download fails
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=s3_key
            )

            sarif_content = response['Body'].read().decode('utf-8')
            logger.debug(f"Downloaded SARIF file from {s3_key}")
            return sarif_content

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                logger.error(f"SARIF file not found: {s3_key}")
            else:
                logger.error(f"Failed to download SARIF file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading SARIF: {e}")
            raise

    def get_presigned_url(
        self,
        s3_key: str,
        expiry: int = 3600,
        filename: Optional[str] = None
    ) -> str:
        """
        Generate presigned URL for SARIF download.

        Allows temporary authenticated access to SARIF files without
        exposing S3 credentials.

        Args:
            s3_key: S3 object key
            expiry: URL expiration time in seconds (default: 1 hour)
            filename: Optional filename for download (Content-Disposition)

        Returns:
            Presigned URL string

        Raises:
            ClientError: If URL generation fails
        """
        try:
            params = {
                'Bucket': self.bucket,
                'Key': s3_key
            }

            # Add Content-Disposition header if filename provided
            if filename:
                params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'

            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiry
            )

            logger.debug(f"Generated presigned URL for {s3_key} (expires in {expiry}s)")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            raise

    def delete_sarif(self, s3_key: str) -> bool:
        """
        Delete SARIF file from S3/MinIO.

        Args:
            s3_key: S3 object key

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            logger.info(f"Deleted SARIF file: {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete SARIF file: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting SARIF: {e}")
            return False

    def get_file_size(self, s3_key: str) -> Optional[int]:
        """
        Get SARIF file size for quota tracking.

        Args:
            s3_key: S3 object key

        Returns:
            File size in bytes, or None if error
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            size = response.get('ContentLength', 0)
            logger.debug(f"File size for {s3_key}: {size} bytes")
            return size

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                logger.warning(f"SARIF file not found: {s3_key}")
            else:
                logger.error(f"Failed to get file size: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting file size: {e}")
            return None

    def list_organization_sarifs(
        self,
        organization_id: str,
        max_keys: int = 1000
    ) -> list:
        """
        List all SARIF files for an organization.

        Args:
            organization_id: Organization UUID
            max_keys: Maximum number of keys to return

        Returns:
            List of S3 object keys
        """
        try:
            prefix = f"{organization_id}/"

            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            contents = response.get('Contents', [])
            keys = [obj['Key'] for obj in contents]

            logger.debug(f"Found {len(keys)} SARIF files for org {organization_id}")
            return keys

        except ClientError as e:
            logger.error(f"Failed to list SARIF files: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing SARIF files: {e}")
            return []

    def calculate_organization_storage(self, organization_id: str) -> int:
        """
        Calculate total storage used by an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            Total size in bytes
        """
        try:
            prefix = f"{organization_id}/"
            total_size = 0

            # List all objects with pagination
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            for page in pages:
                for obj in page.get('Contents', []):
                    total_size += obj.get('Size', 0)

            logger.info(f"Total storage for org {organization_id}: {total_size} bytes")
            return total_size

        except ClientError as e:
            logger.error(f"Failed to calculate storage: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error calculating storage: {e}")
            return 0


# Singleton instance
_storage_instance = None


def get_storage() -> SARIFStorage:
    """
    Get singleton SARIFStorage instance.

    Returns:
        SARIFStorage instance
    """
    global _storage_instance

    if _storage_instance is None:
        _storage_instance = SARIFStorage()

    return _storage_instance
