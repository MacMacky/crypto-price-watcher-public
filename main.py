import boto3
import requests
from dotenv import load_dotenv
import boto3.session
import json
import os
from datetime import datetime

load_dotenv()


COINMARKETCAP_BASE_URL = 'https://pro-api.coinmarketcap.com'
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')
EMAIL_TEMPLATE_NAME = os.getenv('EMAIL_TEMPLATE_NAME')
TO_EMAIL_ADDRESS = os.getenv('TO_EMAIL_ADDRESS')
TO_EMAIL_ADDRESS_ARN = os.getenv('TO_EMAIL_ADDRESS_ARN')
FROM_EMAIL_ADDRESS = os.getenv('FROM_EMAIL_ADDRESS')
FROM_EMAIL_ADDRESS_ARN = os.getenv('FROM_EMAIL_ADDRESS_ARN')
RECEIVING_PHONE_NUMBER = os.getenv('RECEIVING_PHONE_NUMBER')
TABLE_NAME = os.getenv('TABLE_NAME')
REGION = os.getenv('REGION')


IS_SMS_ENABLED = os.getenv('FROM_EMAIL_ADDRESS_ARN') == 'on'
session = boto3.session.Session(
    region_name=REGION,
    profile_name='awsadmin'
)
# https://stackoverflow.com/questions/36390815/how-to-enable-intellisense-for-python-in-visual-studio-code-with-anaconda3
sesv2_client = session.client('sesv2')
sns_client = session.client('sns')
dynamodb_client = session.client('dynamodb')
currencies = ['solana', 'ethereum', 'xrp',
              'cardano', 'hedera', 'sui', 'jupiter-ag']
COINMARKETCAP_API_QUOTE_URL = f"{COINMARKETCAP_BASE_URL}/v2/cryptocurrency/quotes/latest?slug={','.join(currencies)}"

# https://docs.aws.amazon.com/ses/latest/dg/send-personalized-email-api.html
# in USD
threshold_dict = {
    # can also be dictionary form
    'solana': [
        {
            'min': 200,
            'max': 270,
            'name': 'Dipping'
        },
        {
            'min': 150,
            'max': 200,
            'name': 'Interesting'
        },
        {
            'min': 100,
            'max': 150,
            'name': 'Buy "it" now'
        }
    ],
    'sui': [
        {
            'min': 3,
            'max': 3.5,
            'name': 'Dipping'
        },
        {
            'min': 2.75,
            'max': 3,
            'name': 'Interesting'
        },
        {
            'min': 2.5,
            'max': 2.75,
            'name': 'Buy "it" now'
        }
    ],
    'jupiter-ag': [
        {
            'min': 1,
            'max': 1.5,
            'name': "It's going downnnn"
        },
        {
            'min': .9,
            'max': 1,
            'name': 'getting interesting'
        },
        {
            'min': .70,
            'max': .9,
            'name': 'Buy "it" now'
        }
    ],
}


def create_email_content(slug, threshold, min, max):
    return {
        'Template': {
            'TemplateName': EMAIL_TEMPLATE_NAME,
            'TemplateData': {
                'slug': slug,
                'threshold': threshold,
                'min': str(min),
                'max': str(max)
            }
        }
    }


def create_email_template(client):
    client.create_email_template(
        TemplateName=EMAIL_TEMPLATE_NAME,
        TemplateContent={
            'Subject': 'ALERT, ALERT, ALERT PRICE of {{slug}} is going DOWN, threshold {{threshold}}',
            'Text': 'price of {{slug}} is in between {{min}}-{{max}}, please do more research before buying or selling anything.',
            'Html': '<h1>price of {{slug}} is in between {{min}}-{{max}}, please do more research before buying or selling anything.</h1>'
        }
    )


def create_email_template_if_not_exists(client):
    templates = client.list_email_templates()

    if 'TemplatesMetadata' in templates and len(templates['TemplatesMetadata']) > 0:
        existing_templates = templates['TemplatesMetadata']
        template_names = [t['TemplateName'] for t in existing_templates]

        if EMAIL_TEMPLATE_NAME not in template_names:
            create_email_template(client)
        else:
            print(f"Email template '{EMAIL_TEMPLATE_NAME}' already exists.")
    else:
        create_email_template(client)


def request(url, headers):
    result = requests.get(url=url, headers=headers)

    if (result.status_code != 200):
        print(f"Error: status code is {result.status_code} in {url}")
        return

    return result.json()


def send_email_alert(client, slug, threshold):
    client.send_email(
        FromEmailAddress=FROM_EMAIL_ADDRESS,
        FromEmailAddressIdentityArn=FROM_EMAIL_ADDRESS_ARN,
        Destination={
            'ToAddresses': [
                TO_EMAIL_ADDRESS
            ]
        },
        Content={
            'Template': {
                'TemplateName': EMAIL_TEMPLATE_NAME,
                'TemplateData': json.dumps({
                    'slug': slug,
                    'threshold': threshold['name'],
                    'min': str(threshold['min']),
                    'max': str(threshold['max'])
                })
            }
        }
    )
    print(
        f"Successfully sent email for slug: {slug} with threshold name '{threshold['name']}'")


def send_sms_alert(client, slug, threshold, quote_threshold):
    if IS_SMS_ENABLED and RECEIVING_PHONE_NUMBER is not None:
        client.publish(
            PhoneNumber=RECEIVING_PHONE_NUMBER,
            Message=f"Threshold: {threshold['name']} triggered, Quote Amount of {slug} is {quote_threshold} USD...",
            Subject="Crypto Price Alert"
        )


def get_recent_price_item(client, crypto_name):
    items = client.query(TableName=TABLE_NAME,
                         # Can also add the sort or range key here
                         # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.KeyConditionExpressions.html
                         KeyConditionExpression="#N = :value",
                         ExpressionAttributeNames={
                             # "name" is a reserved keyword in DynamoDB so we must use a placeholder
                             # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ReservedWords.html
                             # https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ExpressionAttributeNames.html
                             "#N": "name"
                         },
                         ExpressionAttributeValues={
                             ':value': {
                                 'S':  crypto_name
                             }
                         },
                         # Sort by descending (defaults to True or in ascending)
                         ScanIndexForward=False)
    return items[0] if len(items) > 0 else None


def calculate_percentage_diff(a, b):
    return round((abs(a-b) / ((a+b)/2)) * 100, 2)


def put_price_item(client, crypto_name, current):
    recent = get_recent_price_item(client, crypto_name)

    if recent is None:
        put_item(client, crypto_name, current)

    if current < recent['price'] and calculate_percentage_diff(current, recent['price']) > 10:
        put_item(client, crypto_name, current)

    return None


def put_item(client, crypto_name, price):
    return client.put_item(
        TableName=TABLE_NAME,
        Item={
            'name': {
                'S': crypto_name
            },
            'price': {
                'S': price
            },
            'time_inserted': {
                'S': datetime.now().isoformat()
            }
        },
        ReturnConsumedCapacity="Total",
        ReturnValues='ALL_NEW'
    )


def handler(event, context):
    try:
        create_email_template_if_not_exists(sesv2_client)
        headers = {'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
        response = request(COINMARKETCAP_API_QUOTE_URL, headers)

        if (response is None or response.get('data') is None):
            print('Error: no response data')
            return

        for _, value in response['data'].items():
            slug, quote = value['slug'], value['quote']

            if 'USD' not in quote:
                print('Error: no "USD" in quote')
                continue

            if slug not in threshold_dict:
                print(f"slug '{slug}' not in threshold dictionary")
                continue

            thresholds = threshold_dict[slug]
            slug_quote_in_usd = quote['USD']['price']
            for threshold in thresholds:
                if slug_quote_in_usd > threshold['min'] and slug_quote_in_usd <= threshold['max']:
                    send_email_alert(sesv2_client, slug, threshold)
                    send_sms_alert(sns_client, slug, threshold)
    except Exception as e:
        print(f"error {e}")

    return {
        'value': event['test']
    }
