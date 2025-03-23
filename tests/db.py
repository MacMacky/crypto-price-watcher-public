import unittest
from main import get_previous_price_item, put_item, TABLE_NAME
from testcontainers.localstack import LocalStackContainer


class TestDynamoDB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.localstack = LocalStackContainer('localstack/localstack:stable')
        cls.localstack.start()
        cls.dynamodb_client = cls.localstack.get_client('dynamodb')
        cls.create_table(cls)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.localstack.stop()

    def test_table_list(self):
        response_list_tables = self.dynamodb_client.list_tables()
        self.assertEqual(response_list_tables['TableNames'], [TABLE_NAME])

    def test_table_has_item(self):
        put_item(self.dynamodb_client, 'solana', 100)
        item = get_previous_price_item(self.dynamodb_client, 'solana')
        self.assertIsNotNone(item)

    def create_table(self):
        print(f"Creating table: {TABLE_NAME}")
        self.dynamodb_client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'name',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'inserted_at',
                    'KeyType': 'RANGE'
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'name',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'inserted_at',
                    'AttributeType': 'S'
                },
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 25,
                'WriteCapacityUnits': 25
            }
        )
        print('Done creating table')


if __name__ == '__main__':
    unittest.main()
