"""Show what the (fake) cloud actually stores, for the review demo. Run while fakecloud.py is running:
    infra\\.venv\\Scripts\\python infra\\tests\\inspect_cloud.py
Optionally add words to search for:  ... inspect_cloud.py Suresh Ramesh knife
"""
import io
import os
import sys
import zipfile

os.environ.update(AWS_ENDPOINT_URL="http://127.0.0.1:8798", AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test",
                  AWS_DEFAULT_REGION="ap-south-1")
import boto3  # noqa: E402

WORDS = [w.encode() for w in (sys.argv[1:] or ["Suresh", "Ramesh", "Mani", "knife", "Rs. 5,000", "shop", "police"])]
s3, ddb = boto3.client("s3"), boto3.client("dynamodb")

print("=== DynamoDB: the case index (all the cloud knows about a case) ===")
for item in ddb.scan(TableName="nyaya-cases")["Items"]:
    print({k: list(v.values())[0] for k, v in item.items()})

print("\n=== S3 vault bucket: the objects ===")
found = False
for o in s3.list_objects_v2(Bucket="nyaya-vault").get("Contents", []):
    found = True
    data = s3.get_object(Bucket="nyaya-vault", Key=o["Key"])["Body"].read()
    z = zipfile.ZipFile(io.BytesIO(data))
    print(f"\n{o['Key']}   ({o['Size']} bytes)")
    leaked = []
    for name in z.namelist():
        blob = z.read(name)
        hits = [w.decode() for w in WORDS if w in blob]
        leaked += hits
        print(f"  {name:<48} {len(blob):>6} bytes   starts: {blob[:12].hex()}")
    print("  readable case words found anywhere in this object:", leaked or "NONE")
if not found:
    print("(nothing uploaded yet: upload a case from the app first)")
