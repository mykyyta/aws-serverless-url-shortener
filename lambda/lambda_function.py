import json
import os
import boto3
import hashlib
import base64
import time
from urllib.parse import urlparse

dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("TABLE_NAME")
if not table_name:
    raise RuntimeError("TABLE_NAME environment variable is missing!")

table = dynamodb.Table(table_name)


def handler(event, context):
    """Handles both URL shortening (POST) and redirection (GET)"""

    http_method = event.get("httpMethod")

    if http_method == "POST":
        return shorten_url(event)
    elif http_method == "GET":
        return resolve_url(event)
    else:
        return {"statusCode": 405, "body": json.dumps({"error": "Method Not Allowed"})}


def shorten_url(event):
    """Shortens the URL and ensures unique short_id in DynamoDB"""
    try:
        body = json.loads(event["body"])
        original_url = body.get("url")

        if not original_url or not is_valid_url(original_url):
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid URL"})}

        short_id = None
        for _ in range(5):
            candidate_id = generate_short_id(original_url)
            existing_entry = table.get_item(Key={"short_id": candidate_id})

            if "Item" not in existing_entry:
                short_id = candidate_id
                break  # Found a unique ID

        if not short_id:
            return {"statusCode": 500, "body": json.dumps({"error": "Failed to generate a unique short URL"})}

        # Set TTL (5 minutes expiration)
        ttl_value = int(time.time()) + 300

        # Store in DynamoDB
        table.put_item(Item={"short_id": short_id, "original_url": original_url, "ttl": ttl_value})

        # Get API Gateway URL dynamically
        base_url = f"https://{event['headers']['Host']}/{event['requestContext']['stage']}"
        short_url = f"{base_url}/{short_id}"

        return {"statusCode": 200, "body": json.dumps({"short_url": short_url})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def resolve_url(event):
    path_params = event.get("pathParameters") or {}
    short_id = path_params.get("short_id")

    if not short_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Short ID required"})}

    response = table.get_item(Key={"short_id": short_id})

    if "Item" not in response:
        return {"statusCode": 404, "body": json.dumps({"error": "URL not found"})}

    return {
        "statusCode": 302,
        "headers": {"Location": response["Item"]["original_url"]}
    }


def generate_short_id(url):
    """Generate a short ID"""
    hash_digest = hashlib.md5(url.encode()).digest()
    return base64.urlsafe_b64encode(hash_digest)[:6].decode("utf-8")


def is_valid_url(url):
    """Check if URL is valid"""
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])
