import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway
)

class GlushkoShortenerStack(cdk.Stack):
    def __init__(self, scope: cdk.App, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        table = dynamodb.Table(
            self, "GlushkoShortenerTable",
            table_name="GlushkoShortenerTable",
            partition_key=dynamodb.Attribute(name="short_id", type=dynamodb.AttributeType.STRING),
            time_to_live_attribute="ttl",
            removal_policy=cdk.RemovalPolicy.DESTROY
        )

        url_shortener_lambda = _lambda.Function(
            self, "GlushkoShortenerLambda",
            function_name="GlushkoShortenerLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_function.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "TABLE_NAME": table.table_name
            }
        )

        table.grant_read_write_data(url_shortener_lambda)

        api = apigateway.RestApi(self, "GlushkoShortenerApi",
                                 rest_api_name="GlushkoShortenerApi",
                                 description="API for Glushko URL Shortener"
                                 )

        api.root.add_method("POST", apigateway.LambdaIntegration(url_shortener_lambda))

        short_url_resource = api.root.add_resource("{short_id}")
        short_url_resource.add_method("GET", apigateway.LambdaIntegration(url_shortener_lambda))

        cdk.CfnOutput(self, "ApiUrl", value=api.url)