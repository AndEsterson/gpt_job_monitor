provider "aws" {
  region = ""
  default_tags {
    tags = {
      project = "gpt_job_monitor"
    }
  }
}

resource "aws_ssm_parameter" "gpt_jobs_prompting" {
  name  = "gpt_jobs_prompting"
  type  = "String"
  value = jsonencode(file("${path.module}/prompting.json"))
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

resource "aws_ecr_repository" "gpt_job_monitor" {
  name                 = "gpt_job_monitor"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_lambda_function" "gpt_job_monitor" {
  function_name = "gpt_job_monitor"
  architectures = ["arm64"]
  image_uri     = "${aws_ecr_repository.gpt_job_monitor.repository_url}:latest"
  package_type  = "Image"
  role          = aws_iam_role.iam_for_lambda_jobs.arn
  publish       = true
  timeout       = 300
}

resource "aws_cloudwatch_event_rule" "gpt_job_monitor_trigger" {
  name                = "gpt_job_monitor_trigger"
  schedule_expression = "cron(0 22 * * ? *)"
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.gpt_job_monitor_trigger.name
  target_id = "lambda_target"
  arn       = aws_lambda_function.gpt_job_monitor.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_gpt_job_monitor" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.gpt_job_monitor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.gpt_job_monitor_trigger.arn
}
