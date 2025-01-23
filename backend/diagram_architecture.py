from diagrams import Cluster, Diagram
from diagrams.aws.compute import Lambda
from diagrams.aws.ml import Rekognition
from diagrams.aws.network import APIGateway
from diagrams.aws.storage import S3
from diagrams.aws.mobile import Amplify
from diagrams.aws.database import Dynamodb
from diagrams.aws.security import Cognito

# Create the diagram
with Diagram("Application Architecture"):
    # Frontend with Amplify
    amplify = Amplify("Amplify Frontend")

    # Cognito for authentication
    cognito = Cognito("Cognito")

    # API Gateway
    with Cluster("APIs"):
        api_upload = APIGateway("apiUploadFile")
        api_ocr = APIGateway("apiOCR")

    # Storage Bucket
    s3_bucket = S3("S3 Bucket")

    # Backend logic, Rekognition, and DynamoDB
    with Cluster("Backend"):
        lambda_function = Lambda("Lambda Function")
        rekognition_service = Rekognition("Rekognition")
        dynamodb = Dynamodb("DynamoDB")

    # Define the flow
    amplify >> cognito
    cognito >> api_upload >> s3_bucket
    cognito >> api_ocr >> lambda_function >> rekognition_service
    lambda_function >> dynamodb  # Lambda interacting with DynamoDB
