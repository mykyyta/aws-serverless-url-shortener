import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_ssm as ssm
)

class GlushkoShortenerStack(cdk.Stack):
    def __init__(self, scope: cdk.App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.template_options.description = "Simple URL shortener using API Gateway, Lambda, DynamoDB"

        table = dynamodb.Table(
            self, "GlushkoShortenerTable",
            table_name="GlushkoShortenerTable",
            partition_key=dynamodb.Attribute(name="short_id", type=dynamodb.AttributeType.STRING),
            time_to_live_attribute="ttl",
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        sns_topic = sns.Topic(
            self, "GlushkoShortenerSnsTopic",
            topic_name="GlushkoShortenerNotifications"
        )

        notification_email = ssm.StringParameter.from_string_parameter_name(
            self, "NotificationEmail", "/glushko/notification_email"
        ).string_value
        sns_topic.add_subscription(subscriptions.EmailSubscription(notification_email))

        url_shortener_lambda = _lambda.Function(
            self, "GlushkoShortenerLambda",
            function_name="GlushkoShortenerLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_function.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "TABLE_NAME": table.table_name,
                "SNS_TOPIC_ARN": sns_topic.topic_arn
            }
        )

        table.grant_read_write_data(url_shortener_lambda)

        sns_topic.grant_publish(url_shortener_lambda)

        api = apigateway.RestApi(self, "GlushkoShortenerApi",
                                 rest_api_name="GlushkoShortenerApi",
                                 description="API for Glushko URL Shortener"
                                 )

        api.root.add_method("POST", apigateway.LambdaIntegration(url_shortener_lambda))

        short_url_resource = api.root.add_resource("{short_id}")
        short_url_resource.add_method("GET", apigateway.LambdaIntegration(url_shortener_lambda))

        cdk.CfnOutput(self, "ApiUrl", value=api.url)
        cdk.CfnOutput(self, "SnsTopicArn", value=sns_topic.topic_arn, description="SNS Topic ARN for notifications")
