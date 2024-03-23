import re
import sys
import json
import os
import datetime
import requests
import boto3
from bs4 import BeautifulSoup
from openai import OpenAI

TODAY = datetime.date.today()


def clean_date(date):
    return re.sub(r"(\d)(st|nd|rd|th)", r"\1", date)


def get_job_specifics(url):
    job_specifics = {}
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        job_description_tag = soup.find("div", {"id": "job-description"})
        if job_description_tag:
            job_description_text = job_description_tag.get_text(strip=True)
            job_specifics.update({"description": job_description_text})
        else:
            return {"description": None, "errored": True}
        return job_specifics
    else:
        raise Exception(f"request errored for {url}, {response.status_code}")


def generate_messages_from_prompts(prompting):
    messages = [{"role": "system", "content": prompting["system_prompt"]}]
    for example in prompting["few_shot_prompting"]:
        messages += [
            {"role": "user", "content": example["posting_text"]},
            {"role": "user", "content": example["response"]},
        ]
    return messages


def get_gpt_response(job_description, params):
    client = OpenAI(api_key=params["api_key"])
    prompting = get_parameters("gpt_jobs_prompting")
    messages = generate_messages_from_prompts(prompting)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", temperature=0.4, messages=messages
    )
    return response.choices[0].message.content


def extract_gpt_rating(gpt_response):
    ratings = re.findall(r"\d+\/10", gpt_response)
    return sum([int(rating.split("/")[0]) for rating in ratings]) / len(ratings)


def format_raw_date_placed(posting_date, date_placed):
    return datetime.datetime.strptime(
        f"{date_placed} {posting_date.year}", "%d %b %Y"
    ).date()


def get_job_data(params, url, posting_date):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        job_entries = soup.find_all("div", class_="j-search-result__text")
        jobs = []
        for entry in job_entries:
            href_section = entry.find("a", href=True)
            job_name = href_section.get_text(strip=True)
            job_link = "https://www.jobs.ac.uk" + href_section["href"]
            job_placed_on = format_raw_date_placed(
                posting_date,
                entry.find_parent()
                .find("strong", string=re.compile("Date Placed"))
                .find_parent()
                .text.replace("Date Placed:", "")
                .strip(),
            )
            if job_link.startswith("https://www.jobs.ac.uk/job/"):
                jobs.append(
                    {"name": job_name, "link": job_link, "placed_on": job_placed_on}
                )

        for job in jobs:
            if job["placed_on"] == posting_date:
                job.update(get_job_specifics(job["link"]))
                job.update(
                    {"gpt_response": get_gpt_response(job["description"], params)}
                )
                job.update({"gpt_rating": extract_gpt_rating(job["gpt_response"])})
        jobs = sorted(jobs, key=lambda j: j.get("gpt_rating", 0), reverse=True)
        return jobs
    else:
        raise Exception(
            f"Failed to retrieve the webpage. Status Code: {response.status_code}"
        )


def filter_jobs(jobs):
    for job in jobs:
        if job.get("gpt_rating", 0) > 6:
            job.update({"important": True})
        else:
            job.update({"important": False})


def get_parameters(parameter_name):
    client = boto3.client("ssm")
    response = client.get_parameter(Name=parameter_name)
    return json.loads(response["Parameter"]["Value"])


def send_email(
    source, destination, important_jobs, unimportant_jobs, date, job_posting_name
):
    email_body = ""
    for job in important_jobs:
        email_body += "\n" + job["name"] + "\n"
        email_body += job["link"] + "\n"
        email_body += job["gpt_response"] + "\n"
    email_body += "\n-------------------\n"
    for job in unimportant_jobs:
        email_body += "\n" + job["name"] + "\n"
        email_body += (
            job["link"] + " " + str(job.get("gpt_rating", "null")) + "/10" + "\n"
        )
    client = boto3.client("ses")
    response = client.send_email(
        Source=source,
        Destination={
            "ToAddresses": [
                destination,
            ]
        },
        Message={
            "Subject": {"Data": f"Postings for {job_posting_name} - {date}"},
            "Body": {
                "Text": {
                    "Data": email_body,
                }
            },
        },
    )


def lambda_handler(event, context):
    if {"email_source", "email_destination", "api_key", "job_postings"} - event.keys():
        params = get_parameters("gpt_jobs_parameters")
    else:
        params = event
    for job_posting in params["job_postings"]:
        posting_date = TODAY - datetime.timedelta(params.get("shift_by_days", 0))
        jobs = get_job_data(params, job_posting["url"], posting_date)
        filter_jobs(jobs)
        send_email(
            params["email_source"],
            params["email_destination"],
            [
                job
                for job in jobs
                if job["important"]
                and job.get("placed_on") == params.get("date", posting_date)
            ],
            [
                job
                for job in jobs
                if not job["important"]
                and (
                    job.get("placed_on", None) == posting_date
                    or job.get("errored", False)
                )
            ],
            posting_date,
            job_posting["name"],
        )


def read_json(path):
    with open(path) as json_file:
        return json.load(json_file)


if __name__ == "__main__":
    event = {
        "email_source": sys.argv[1],
        "email_destination": sys.argv[2],
        "api_key": sys.argv[3],
        "shift_by_days": int(sys.argv[4]),
        "job_postings": read_json(sys.argv[5]),
    }
    context = ""
    lambda_handler(event, context)
