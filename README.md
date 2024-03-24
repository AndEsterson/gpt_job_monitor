# gpt job monitor

This project is intended to replace the fairly simple keyword-based job alerts that jobs.ac.uk provides, it parses html to extract info on each job posted that day (from a list of jobs.ac.uk filter pages provided by the user), sends each description to chatgpt and ranks according to user defined preferences, sending an email to the user for each filter page, including the rankings of all jobs, links to each posting and short gpt responses for highly ranked jobs.

# Infrastructure

The code itself runs in a docker container, the image for this is built, pushed to an ECR repository, then used for the lambda function. The lambda function is called nightly by Cloudwatch and relies on AWS Parameter Store to retrieve parameters for the run as well as AWS SES to send an email to the user.

# Setup

1) clone this repository
2) register an openai apikey
3) write your own ./prompting.json using the ./example_prompting.json file, this contains information about your job preferences
4) write the `gpt_jobs_parameters` value in AWS Parameter Store which is of format 
```{"email_source": <ses_registered_email, "email_destination": <user_email>, "api_key": <openai_api_key>, "job_postings": ["name": <name_used_in_email>, "url": <url_from_jobs.ac.uk>]```
5) run `terraform apply -target aws_ecr_repository.gpt_job_monitor && aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com && docker build . -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/gpt-job-monitor:latest && docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/gpt-job-monitor:latest`
6) run `terraform apply`
