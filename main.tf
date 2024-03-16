provider "aws" {
  region = ""
  default_tags {
    tags = {
      project = "gpt_job_monitor"
    }
  }
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "allow_ssm_read" {
  statement {
    effect = "Allow"
    actions = [
      "ssm:GetParameterHistory",
      "ssm:GetParametersByPath",
      "ssm:GetParameters",
      "ssm:GetParameter"
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "allow_ses_send" {
  statement {
    effect = "Allow"
    actions = [
      "ses:SendEmail",
      "ses:SendRawEmail"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "iam_for_lambda_jobs" {
  name               = "gpt_job_monitor_role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
  inline_policy {
    name   = "allow_ssm_read"
    policy = data.aws_iam_policy_document.allow_ssm_read.json
  }
  inline_policy {
    name   = "allow_ses_send"
    policy = data.aws_iam_policy_document.allow_ses_send.json
  }
}

data "archive_file" "lambda_gpt_job_monitor" {
  type        = "zip"
  source_dir  = "src"
  output_path = "lambda_gpt_payload.zip"
}

resource "aws_lambda_function" "gpt_job_monitor" {
  filename         = "lambda_gpt_payload.zip"
  function_name    = "gpt_job_monitor"
  role             = aws_iam_role.iam_for_lambda_jobs.arn
  handler          = "main.lambda_handler"
  timeout          = 900
  architectures    = ["arm64"]
  source_code_hash = data.archive_file.lambda_gpt_job_monitor.output_base64sha256
  runtime          = "python3.11"
}

