from __future__ import print_function
# python manage.py dumpdata flatblocks --output flatblocks_heroku.json

from boto.s3.connection import S3Connection
from boto.s3.key import Key
import os

AWS_KEY_ID = os.environ['AWS_KEY_ID']
AWS_SECRET_ID = os.environ['AWS_SECRET_ID']
AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']

aws_connection = S3Connection(AWS_KEY_ID, AWS_SECRET_ID)
bucket = aws_connection.get_bucket(AWS_STORAGE_BUCKET_NAME)

k = Key(bucket)

content_type = {"css": "text/css",
                "js": "application/javascript",
                "gif": "image/gif",
                "png": "image/png",
                "jpg": "image/jpeg",
                "svg": "image/svg+xml",
                "txt": "text/plain",
                "ttf": "application/x-font-ttf",
                "woff": "application/x-font-woff",
                "woff2": "application/octet-stream",
                "scss": "application/octet-stream",
                "eot": "application/vnd.ms-fontobject",
                "swf": "application/application/x-shockwave-flash",
                "less": "application/octet-stream"}

for root, dirs, files in os.walk("."):
    for f in files:
        if f.endswith("py"):
            continue
        if (f.endswith(".css") or f.endswith(".js") or
                f.endswith("png") or f.endswith("jpg")):
            full_path = os.path.join(root, f)[2:]
            bucket_path = full_path
            print(bucket_path)
            ext = f[f.rfind('.') + 1:]
            print(content_type[ext])
            print(os.path.join(root, f))
            k = Key(bucket)
            k.key = bucket_path
            if f.endswith("png") or f.endswith("jpg"):
                headers = {'Content-Type': content_type[ext]}
            else:
                headers = {'Content-Type': content_type[ext],
                           'Content-Encoding': 'gzip'}
            k.set_contents_from_filename(full_path, headers=headers)
