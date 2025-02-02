terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.78.0"
    }


  }
}
provider "aws" {
  region = "us-east-1"
}


resource "aws_ami" "main" {
  name             = "test-ami-mark"
  root_device_name = "/dev/sda1"
  architecture     = "x86_64"

  ebs_block_device {
    device_name           = "/dev/sda1"
    delete_on_termination = true
    snapshot_id           = aws_ebs_snapshot.first_snapshot.id
  }
}


resource "aws_ebs_volume" "main_storage" {
  availability_zone = "ap-east-1a"
  size              = 8
}


resource "aws_ebs_snapshot" "first_snapshot" {
  volume_id    = aws_ebs_volume.main_storage.id
  storage_tier = "standard"
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

