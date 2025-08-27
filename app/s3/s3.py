import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from aiobotocore.session import get_session

load_dotenv()

class S3Client:
    def __init__(self,
                 access_key: str,
                 secret_key: str,
                 endpoint_url: str,
                 bucket_name: str,):
        self.config = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key":secret_key,
            "endpoint_url": endpoint_url,
            "verify": False,
        }
        self.bucket_name = bucket_name
        self.session = get_session()

    @asynccontextmanager
    async def get_client(self):
        async with self.session.create_client("s3", **self.config) as client:
            yield client

    async def upload_file(self,file_path: str,object_name:str,):
        async with self.get_client() as client:
            with open(file_path, "rb") as file:
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=file
                )

if __name__ == "__main__":
    s3_client = S3Client(
        access_key=os.getenv("S3_ACCESS_KEY"),
        secret_key=os.getenv("S3_SECRET_KEY"),
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        bucket_name=os.getenv("S3_BUCKET_NAME")
    )
