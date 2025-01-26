import boto3
import requests
from dotenv import load_dotenv
import boto3.session
import json
import os

load_dotenv()


COINMARKETCAP_BASE_URL = 'https://pro-api.coinmarketcap.com'
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')
EMAIL_TEMPLATE_NAME = os.getenv('EMAIL_TEMPLATE_NAME')
TO_EMAIL_ADDRESS = os.getenv('TO_EMAIL_ADDRESS')
TO_EMAIL_ADDRESS_ARN = os.getenv('TO_EMAIL_ADDRESS_ARN')
FROM_EMAIL_ADDRESS = os.getenv('FROM_EMAIL_ADDRESS')
FROM_EMAIL_ADDRESS_ARN = os.getenv('FROM_EMAIL_ADDRESS_ARN')
REGION = os.getenv('REGION')

session = boto3.session.Session(
    region_name=REGION,
    profile_name='awsadmin'
)


currencies = ['solana', 'ethereum', 'xrp', 'cardano', 'hedera']

# https://stackoverflow.com/questions/36390815/how-to-enable-intellisense-for-python-in-visual-studio-code-with-anaconda3
sesv2_client = session.client('sesv2')


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


def handler(event, context):
    try:
        create_email_template_if_not_exists(sesv2_client)
        headers = {'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
        result = requests.get(
            f"{COINMARKETCAP_BASE_URL}/v2/cryptocurrency/quotes/latest?slug={','.join(currencies)}", headers=headers)

        if (result.status_code != 200):
            print(f"Error: status code is {result.status_code}")
            return

        response = result.json()

        if (response['data'] is None):
            print('Error: no response data')
            return

        for _, value in response['data'].items():
            slug, quote = value['slug'], value['quote']

            if 'USD' not in quote:
                print('Error: no "USD" in quote')

            if slug in threshold_dict:
                thresholds = threshold_dict[slug]
                slug_quote_in_usd = quote['USD']['price']
                for threshold in thresholds:
                    if slug_quote_in_usd > threshold['min'] and slug_quote_in_usd <= threshold['max']:
                        sesv2_client.send_email(
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
    except Exception as e:
        print(f"error {e}")

    return {
        'value': event['test']
    }


handler({'test': 'test', }, {})
