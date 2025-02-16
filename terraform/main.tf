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


# Lambda
resource "aws_lambda_function" "crypto_price_alert" {
  function_name    = "crypto_price_alert"
  architectures    = ["x86_64"]
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "api.handler"
  runtime          = "python3.11"
  filename         = "${path.module}/function.zip"
  source_code_hash = filebase64sha256("${path.module}/function.zip")
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

