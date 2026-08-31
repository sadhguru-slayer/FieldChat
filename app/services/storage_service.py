import boto3
import json
from botocore.client import Config
from app.config import settings

class StorageService:
    def __init__(self):
        # OCI Object Storage is fully S3 compatible. We configure the client with
        # signature_version='s3v4' to satisfy OCI requirements.
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION_NAME,
            config=Config(signature_version="s3v4"),
        )

    def init_bucket(self):
        bucket_name = settings.S3_BUCKET_NAME
        try:
            # Check if bucket exists
            self.s3.head_bucket(Bucket=bucket_name)
            print(f"[StorageService] Bucket '{bucket_name}' already exists.", flush=True)
        except Exception:
            try:
                # Attempt to create bucket if it doesn't exist
                print(f"[StorageService] Attempting to create bucket: '{bucket_name}'", flush=True)
                self.s3.create_bucket(Bucket=bucket_name)
                print(f"[StorageService] Successfully created bucket '{bucket_name}'", flush=True)
                
                # Configure a public read-only policy for this bucket
                # (Supported by MinIO, but will fail/be ignored in OCI where bucket policies are managed in IAM)
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadGetObject",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
                        }
                    ]
                }
                self.s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
                print(f"[StorageService] Successfully set public read policy on bucket '{bucket_name}'", flush=True)
            except Exception as e:
                print(f"[StorageService Warning] Could not auto-initialize bucket/policy for '{bucket_name}': {e}. "
                      "Ensure the bucket has been pre-created and configured with appropriate IAM/read policies.", flush=True)

    def upload_file(self, file, object_name):
        self.s3.upload_fileobj(file, settings.S3_BUCKET_NAME, object_name)

    def download_file(self, object_name):
        return self.s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=object_name)

    def delete_file(self, object_name):
        try:
            print(f"[StorageService] Attempting to delete object: '{object_name}' from bucket: '{settings.S3_BUCKET_NAME}'", flush=True)
            self.s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=object_name)
            print(f"[StorageService] Successfully deleted object: '{object_name}'", flush=True)
            return True
        except Exception as e:
            print(f"[StorageService Error] Failed to delete object '{object_name}': {e}", flush=True)
            return False

    def delete_media_by_url(self, media_url):
        if not media_url:
            print("[StorageService Warning] Empty media_url received for deletion.", flush=True)
            return False
        
        print(f"[StorageService] Parsing media URL for deletion: '{media_url}'", flush=True)
        prefix = f"/{settings.S3_BUCKET_NAME}/"
        if prefix in media_url:
            object_name = media_url.split(prefix, 1)[1]
        elif media_url.startswith(prefix):
            object_name = media_url[len(prefix):]
        else:
            parts = media_url.strip("/").split("/")
            if len(parts) >= 2:
                object_name = parts[-1]
            else:
                object_name = media_url
        
        if "?" in object_name:
            object_name = object_name.split("?", 1)[0]
            
        return self.delete_file(object_name)
