import json
import os
import boto3
import time
import hashlib
from urllib.parse import urlparse

dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

table_name = os.environ["TABLE_NAME"]
sns_topic_arn = os.environ["SNS_TOPIC_ARN"]
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
    """Shortens the URL and sends a notification"""
    try:
        body = json.loads(event["body"])
        original_url = body.get("url")

        if not original_url or not is_valid_url(original_url):
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid URL"})}

        short_id = generate_short_id(original_url)

        ttl_value = int(time.time()) + 300

        table.put_item(Item={"short_id": short_id, "original_url": original_url, "ttl": ttl_value})

        base_url = f"https://{event['headers']['Host']}/{event['requestContext']['stage']}"
        short_url = f"{base_url}/{short_id}"

        sns_client.publish(
            TopicArn=sns_topic_arn,
            Subject="New Shortened URL Created",
            Message=(
                f"A new short URL was created!\n\n"
                f"Short Link: {short_url}\n"
                f"Original URL: {original_url}\n"
                f"Expires in: 5 minutes"
            )
        )

        return {"statusCode": 200, "body": json.dumps({"short_url": short_url})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def resolve_url(event):
    """Resolves short URL, deletes it after access, and sends a notification"""
    path_params = event.get("pathParameters") or {}
    short_id = path_params.get("short_id")

    if not short_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Short ID required"})}

    response = table.get_item(Key={"short_id": short_id})

    if "Item" not in response:
        return {"statusCode": 404, "body": json.dumps({"error": "URL not found"})}

    original_url = response["Item"]["original_url"]

    table.delete_item(Key={"short_id": short_id})

    sns_client.publish(
        TopicArn=sns_topic_arn,
        Subject="Shortened URL Accessed",
        Message=(
            f"A user accessed a shortened URL!\n\n"
            f"Short Link ID: {short_id}\n"
            f"Redirected to: {original_url}"
        )
    )

    return {
        "statusCode": 302,
        "headers": {"Location": original_url}
    }


def generate_short_id(url):
    """Generate a unique short ID"""
    hash_digest = hashlib.md5((url + str(time.time())).encode()).hexdigest()
    return hash_digest[:6]


def is_valid_url(url):
    """Check if URL is valid"""
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])
