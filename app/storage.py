import os
from io import BytesIO
from minio import Minio
from minio.error import S3Error
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "rabbit-media")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "False").lower() in ("true", "1", "t")

if not MINIO_ROOT_USER or not MINIO_ROOT_PASSWORD:
    raise RuntimeError("MinIO credentials (MINIO_ROOT_USER, MINIO_ROOT_PASSWORD) not found in environment or .env file!")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ROOT_USER,
    secret_key=MINIO_ROOT_PASSWORD,
    secure=MINIO_USE_SSL
)

def ensure_bucket_exists():
    """Ensure the configured MinIO bucket exists, create if not."""
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET_NAME):
            minio_client.make_bucket(MINIO_BUCKET_NAME)
            print(f"Created MinIO bucket: {MINIO_BUCKET_NAME}")
    except S3Error as e:
        print(f"MinIO bucket check/creation error: {e}")

def upload_file_to_minio(file_bytes: bytes, object_name: str, content_type: str = "image/jpeg") -> str:
    """
    Uploads a file to MinIO with a user-scoped prefix
    (e.g. users/{user_id}/avatars/{rabbit_id}.jpg or users/{user_id}/scans/{rabbit_id}/{scan_id}.jpg).
    Returns the relative media path: /media/{object_name}
    """
    ensure_bucket_exists()
    file_stream = BytesIO(file_bytes)
    minio_client.put_object(
        bucket_name=MINIO_BUCKET_NAME,
        object_name=object_name,
        data=file_stream,
        length=len(file_bytes),
        content_type=content_type,
    )
    return f"/media/{object_name}"

def get_file_from_minio(object_name: str):
    """Retrieves a file stream from MinIO."""
    ensure_bucket_exists()
    return minio_client.get_object(MINIO_BUCKET_NAME, object_name)

def delete_file_from_minio(object_name: str):
    """Deletes an object from MinIO."""
    try:
        minio_client.remove_object(MINIO_BUCKET_NAME, object_name)
    except Exception as e:
        print(f"Error deleting {object_name} from MinIO: {e}")
