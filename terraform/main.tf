terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.78.0"
    }
  }
}

provider "aws" {
  profile = "awsadmin"
  region  = "us-east-1"
}


# CloudWatch Event Rule (now "EventBridge") 
## https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_rule
## https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_target
# CloudWatch Event Rule Role


# Lambda Function
# IAM Role with Trust Policy (for CloudWatch Event Rule)

# IAM Role with Trust Policy (for CloudWatch Event Rule)
# Inline Policy with permission "lambda:InvokeFunction", specify resource

# IAM Role with Trust Policy (for Lambda)
# Inline Policy with permissions for SES and SNS SMS actions

# (Optional) SQS Dead Letter Queue

