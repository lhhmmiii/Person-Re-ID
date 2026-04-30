from minio import Minio
from io import BytesIO
from datetime import timedelta
from typing import List

class MinioUtils:
    def __init__(
        self, 
        bucket_name: str, 
        endpoint: str,
        access_key: str,
        secret_key: str
    ):
        self.bucket_name = bucket_name
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )

    def create_bucket(self):
        """
        Create a bucket if it does not exist
        """
        found = self.client.bucket_exists(self.bucket_name)
        if not found:
            self.client.make_bucket(self.bucket_name)
            print(f"Bucket {self.bucket_name} created successfully")
        else:
            print(f"bucket {self.bucket_name} already exists")

    def check_object_name_exists(self, object_name: str):
        """
        Check if an object name exists in a bucket
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except Exception as e:
            return False
    

    def upload_bytes(self, file_data: bytes, object_name: str, content_type: str):
        """
        Upload a file to a bucket
        """
        try:
            # Check if the object name exists
            if self.check_object_name_exists(object_name):
                print(f"Object {object_name} already exists")
            
            # Put the object into the bucket
            data_stream = BytesIO(file_data)
            data_stream.seek(0)
            length = len(file_data)
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data_stream,
                content_type=content_type,
                length=length,
            )
            
        except Exception as e:
            raise Exception(e)
        
    def upload_file(self, file_path: bytes, object_name: str, content_type: str) -> str:
        """
        Upload a file to a bucket
        """
        try:
            # Check if the object name exists
            if self.check_object_name_exists(object_name):
                print(f"Object {object_name} already exists")
                return self.presigned_get_object(object_name=object_name)
            
            # Put the object into the bucket
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type
            )
            
            # Get the presigned URL for the object
            url = self.presigned_get_object(object_name=object_name)
            return url
        except Exception as e:
            raise Exception(e)

    def presigned_get_object(self, object_name: str)->str:
        """
        Get a presigned URL for a file expires in 7 days
        """
        return self.client.presigned_get_object(
            bucket_name=self.bucket_name, 
            object_name=object_name, 
            expires=timedelta(days=7)
        )
        
    def get_minio_bytes(self, object_name):
        """
        Get object bytes
        """
        resp = self.client.get_object(self.bucket_name, object_name)
        data = resp.read()
        resp.close()
        resp.release_conn()
        return data
    
    def list_objects(self, prefix: str = "", recursive: bool = True) -> List[str]:
        """Return all object names under a given prefix."""
        objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=recursive)
        return [obj.object_name for obj in objects]