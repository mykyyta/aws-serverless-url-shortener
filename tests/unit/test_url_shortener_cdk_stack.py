import aws_cdk as core
import aws_cdk.assertions as assertions

from url_shortener_cdk.url_shortener_cdk_stack import UrlShortenerCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in url_shortener_cdk/url_shortener_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = UrlShortenerCdkStack(app, "url-shortener-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
