import boto3

# https://stackoverflow.com/questions/36390815/how-to-enable-intellisense-for-python-in-visual-studio-code-with-anaconda3
ses_client = boto3.client('sesv2')


def handler(event, context):
    return {
        "value": event['test']
    }
