terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.78.0"
    }
  }

  backend "s3" {
    bucket         = "macky-tfstate-bucket"
    key            = "crypto-price-alert-infra.tfstate"
    dynamodb_table = "macky_tfstate"
    region         = "us-east-1"
  }
}
provider "aws" {
  region = "us-east-1"
}

locals {
  function_name = "crypto_price_alert"
}

# CloudWatch Event Rule
resource "aws_cloudwatch_event_rule" "crypto_price_job" {
  name                = "crypto_price_job"
  schedule_expression = "rate(30 minutes)"
}

# CloudWatch Event Rule Permission to Invoke Lambda Function `crypto_price_alert`
resource "aws_lambda_permission" "allow_cloudwatch_event_rule" {
  function_name = aws_lambda_function.crypto_price_alert.function_name
  action        = "lambda:InvokeFunction"
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.crypto_price_job.arn
}

# CloudWatch Event Target
resource "aws_cloudwatch_event_target" "function_target" {
  arn  = aws_lambda_function.crypto_price_alert.arn
  rule = aws_cloudwatch_event_rule.crypto_price_job.name
}

data "aws_ssm_parameter" "coinmarket_api_key" {
  name            = "/${local.function_name}/COINMARKETCAP_API_KEY"
  with_decryption = true
}
data "aws_ssm_parameter" "from_email_address" {
  name            = "/${local.function_name}/FROM_EMAIL_ADDRESS"
  with_decryption = true
}

data "aws_ssm_parameter" "from_email_address_arn" {
  name            = "/${local.function_name}/FROM_EMAIL_ADDRESS_ARN"
  with_decryption = true
}

data "aws_ssm_parameter" "to_email_address" {
  name            = "/${local.function_name}/TO_EMAIL_ADDRESS"
  with_decryption = true
}

data "aws_ssm_parameter" "to_email_address_arn" {
  name            = "/${local.function_name}/TO_EMAIL_ADDRESS_ARN"
  with_decryption = true
}

data "aws_ssm_parameter" "receiving_phone_number" {
  name            = "/${local.function_name}/RECEIVING_PHONE_NUMBER"
  with_decryption = true
}


# Lambda
resource "aws_lambda_function" "crypto_price_alert" {
  function_name    = local.function_name
  architectures    = ["x86_64"]
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "main.handler"
  runtime          = "python3.11"
  filename         = "function.zip"
  source_code_hash = filebase64sha256("function.zip")

  environment {
    variables = {
      COINMARKETCAP_API_KEY  = data.aws_ssm_parameter.coinmarket_api_key.value
      FROM_EMAIL_ADDRESS     = data.aws_ssm_parameter.from_email_address.value
      FROM_EMAIL_ADDRESS_ARN = data.aws_ssm_parameter.from_email_address_arn.value
      TO_EMAIL_ADDRESS       = data.aws_ssm_parameter.to_email_address.value
      TO_EMAIL_ADDRESS_ARN   = data.aws_ssm_parameter.to_email_address_arn.value
      RECEIVING_PHONE_NUMBER = data.aws_ssm_parameter.receiving_phone_number.value
    }
  }
}


# Lambda Role 
resource "aws_iam_role" "lambda_execution_role" {
  name               = "crypto_price_alert_execution_role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_doc.json
}

# Lambda Assume Role Policy Document
data "aws_iam_policy_document" "lambda_assume_doc" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Lambda Role Inline Policy Document
resource "aws_iam_role_policy" "lambda_inline_permission_policy" {
  name   = "lambda_inline_permission_policy"
  role   = aws_iam_role.lambda_execution_role.id
  policy = data.aws_iam_policy_document.lambda_permission_policy_doc.json
}


data "aws_iam_policy_document" "lambda_permission_policy_doc" {
  statement {
    # For DynamoDB
    actions = [
      "dynamodb:Query",
      "dynamodb:PutItem"
    ]
    effect = "Allow"
    # add principal only specific lambda arn
    resources = [
      aws_dynamodb_table.recent_crypto_prices.arn,
      // for querying Primary key (hash key + range key)
      "${aws_dynamodb_table.recent_crypto_prices.arn}/index/*"
    ]
  }


  statement {
    # For CloudWatch
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    effect    = "Allow"
    resources = ["*"]
  }

  statement {
    # For SES (Simple Email Service)
    effect = "Allow"
    actions = [
      "ses:SendEmail",
      "ses:ListEmailIdentities"
    ]
    resources = ["*"]
  }
}

# DynamoDB Table
resource "aws_dynamodb_table" "recent_crypto_prices" {
  name           = "recent_crypto_prices"
  billing_mode   = "PROVISIONED"
  read_capacity  = 25
  write_capacity = 25
  hash_key       = "name"
  range_key      = "inserted_at"

  attribute {
    type = "S"
    name = "name"
  }

  attribute {
    type = "S"
    name = "inserted_at"
  }

  ttl {
    enabled        = true
    attribute_name = "expires_at"
  }
}

