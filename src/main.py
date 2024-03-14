import re
import sys
import json
import requests
import datetime
import send_email
import boto3
from bs4 import BeautifulSoup
from openai import OpenAI

TODAY = datetime.date.today()

example_qualified_job_posting = """
Do you hold an MSc or PhD in artificial intelligence, data science or software engineers?

Do you have a strong background in data analytics and software development?

Would you like to work with an industry leading company to develop cutting edge data optimisation tools? 

The University of Leeds has an opportunity for you to ‘fast track’ your career in industry by leading a project to develop, deploy and embed an advanced, AI-driven code optimisation techniques to intelligently increase efficiency and output of software programs within the financial sector. Through a Knowledge Transfer Partnership (KTP), you will be working in collaboration with a sector leading artifical intelligence company, TurinTech, and Leeds University’s School of Computing.

As a KTP Associate, you will be expected to manage this project and effectively transfer knowledge from the academic knowledge base at The University of Leeds to TurinTech. You will be working closely with academics in the School of Computing and TurinTech’s team of experienced software engineers to create an innovative and robust software development tool that is able to strengthen existing and accelerate future software development.

TurinTech is an innovative and groundbreaking artifical intelligence company whose mission is to create machine learning based tools to facilitate enhanced software development, most notably through their flagship product, Artemis. TurinTech’s reputation within the finance sector is growing  all the time, with a client base that includes well-known organisations such as Exasol, Lloyds Banking Group, and XY Capital.
"""

example_qualified_job_response = """
This job has the kind of work you are interested in. You do not hold an MSc or PhD in artificial intelligence, data science or software engineering,
but you do have experience through work, so you may have enough experience for the position. 6/10
"""

example_under_qualified_job_posting = """
The Department of Information Security is seeking to appoint a senior lecturer in Information Security and welcomes applications from a broad range of areas related to information security, especially those with expertise and experience in network security, systems security, software security and applications of AI in security.

This post will have specific responsibility for leading and directing our MSc in Information Security. The post holder will be expected to produce high quality publications, attract significant research funding, direct and manage our flagship Information Security MSc and be able to deliver both excellent undergraduate and postgraduate teaching and project supervision. The post holder will also be expected to contribute strongly to the development of research impact and the undertaking of knowledge exchange. Applicants with a strong track record across these aspects of the post are encouraged to apply.

The Department of Information Security has a record of outstanding research and hosts established research groups under the themes of: People and Society, Systems and Software Security, Smart Card and Internet of Things Security, and Cryptography. We are committed to delivering excellent teaching at both undergraduate and postgraduate level. Our MSc in Information Security, the first of its kind anywhere in the world when it was launched in 1992, is accredited by The National Cyber Security Centre (NCSC) and has over 4,000 alumni worldwide. The Department has received an ACE-CSE Gold Award recognising excellence in cyber security education from the NCSC. The Department is part of Royal Holloway’s School of Engineering, Physical and Mathematical Sciences (EPMS) and it plays an active part in inter-disciplinary activities.
"""
example_under_qualified_job_response = """
This job may involve some programming elements, but it is mainly a research position.
You also do not meet the criteria for a senior lecturer position, which likely requires a PhD. 2/10
"""

def clean_date(date):
    return re.sub(r'(\d)(st|nd|rd|th)', r'\1', date)

def get_job_specifics(url):
    job_specifics = {}
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        job_description_tag = soup.find('div', {'id': 'job-description'})
        if job_description_tag:
            job_description_text = job_description_tag.get_text(strip=True)
            job_specifics.update({'description': job_description_text})
        else:
            return {'description': None, 'errored': True}
        return job_specifics
    else:
        raise Exception(f"request errored for {url}, {response.status_code}")
        
def get_gpt_response(job_description, params):
    client = OpenAI(api_key=params['api_key'])
    response = client.chat.completions.create(
  model="gpt-3.5-turbo",
  temperature=0.4,
  messages=[
        {"role": "system", "content": """
        You give brief answers ranking the relevance of job postings for a person with the following description:
        I have a master's degree in physics, with a project involving computational neuroscience. Since graduating,
        I have ~18 months of experience as a DevOps engineer, working with Python, Bash, AWS, terraform, kubernetes, git, postgreSQL.
        I do not hold a PhD, and don't have experience lecturing or doing experimental lab work.
        If the position is a software development position (or similar) then give no lower a score than 4/10
        I am looking for jobs that involve programming, especially cloud hosting or CI/CD, bonus points for roles with an ethical value. Jobs in humanities fields should be ranked lower and jobs in STEM fields should be ranked more lowly, senior positions and positions that require a PhD should be ranked lowly
        You give a brief description of the benefits of the job and an overall score out of 10 based on value and relevancy of the person's experience, ensure your recommendations are accurate to the experience of the person. Take a deep breath before answering.
        """},
        {"role": "user", "content": example_under_qualified_job_posting},
        {"role": "assistant", "content": example_under_qualified_job_response},
        {"role": "user", "content": example_qualified_job_posting},
        {"role": "assistant", "content": example_qualified_job_response},
        {"role": "user", "content": job_description},
        ]
    )
    return response.choices[0].message.content

def extract_gpt_rating(gpt_response):
    ratings = re.findall("\d+\/10", gpt_response)
    return sum([int(rating.split('/')[0]) for rating in ratings])/len(ratings)

def format_raw_date_placed(posting_date, date_placed):
    return datetime.datetime.strptime(f"{date_placed} {posting_date.year}", '%d %b %Y').date()

def get_job_data(params, url, posting_date):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        job_entries = soup.find_all('div', class_='j-search-result__text')
        jobs = []
        for entry in job_entries:
            href_section = entry.find('a', href=True)
            job_name = href_section.get_text(strip=True)
            job_link = "https://www.jobs.ac.uk" + href_section['href']
            job_placed_on = format_raw_date_placed(
                            posting_date,
                            entry.find_parent()
                                .find('strong', string=re.compile('Date Placed'))
                                .find_parent()
                                .text
                                .replace('Date Placed:', '')
                                .strip()
                            )
            if job_link.startswith("https://www.jobs.ac.uk/job/"):
                jobs.append({'name': job_name, 'link': job_link, 'placed_on': job_placed_on})

        for job in jobs:
            if job['placed_on'] == posting_date:
                job.update(get_job_specifics(job['link']))
                job.update({'gpt_response': get_gpt_response(job['description'], params)})
                job.update({'gpt_rating': extract_gpt_rating(job['gpt_response'])})
        jobs = sorted(jobs, key=lambda j: j.get("gpt_rating", 0), reverse=True)
        return jobs
    else:
        raise Exception(f"Failed to retrieve the webpage. Status Code: {response.status_code}")

def filter_jobs(jobs):
    for job in jobs:
        if job.get("gpt_rating", 0) > 6:
            job.update({'important': True})
        else:
            job.update({'important': False})

def get_parameters():
    client = boto3.client("ssm")
    response = client.get_parameter(
        Name="gpt_jobs_parameters"
    )
    return json.loads(response['Parameter']['Value'])

def lambda_handler(event, context):
    if ({'email_source', 'email_destination', 'api_key'} - event.keys()):
        params = get_parameters()
    else:
        params = event
    for job_posting in params['job_postings']:
        posting_date = TODAY - datetime.timedelta(params.get("shift_by_days", 0))
        jobs = get_job_data(params, job_posting['url'], posting_date)
        filter_jobs(jobs)
        send_email.send_email(params['email_source'], params['email_destination'], 
                [job for job in jobs if job['important'] and job.get("placed_on") == params.get("date", posting_date)],
                [job for job in jobs if not job['important'] and (job.get("placed_on", None) == posting_date or job.get("errored", False))], posting_date, job_posting['name'])

if __name__ == "__main__":
    job_postings = [
            {'name': 'London', 'url': 'https://www.jobs.ac.uk/search/?location=London%2C+UK&locationCoords%5B0%5D=51.5072178%2C-0.1275862&locality%5B0%5D=London&administrativeAreaLevel1%5B0%5D=England&administrativeAreaLevel2%5B0%5D=Greater+London&country%5B0%5D=United+Kingdom&country%5B1%5D=GB&distance=0&placeId=ChIJdd4hrwug2EcRmSrV3Vo6llI&activeFacet=nonAcademicDisciplineFacet&sortOrder=1&pageSize=1000&startIndex=1'},
            {'name': 'Cambridge', 'url': 'https://www.jobs.ac.uk/search/?location=Cambridge%2C+UK&locationCoords%5B0%5D=52.1950788%2C0.1312729&locality%5B0%5D=Cambridge&administrativeAreaLevel1%5B0%5D=England&administrativeAreaLevel2%5B0%5D=Cambridgeshire&country%5B0%5D=United+Kingdom&country%5B1%5D=GB&distance=0&placeId=ChIJLQEq84ld2EcRIT1eo-Ego2M&sortOrder=1&pageSize=1000&startIndex=1'}
        ]
    event = {'email_source': sys.argv[1], 'email_destination': sys.argv[2], 'api_key': sys.argv[3], 'shift_by_days': int(sys.argv[4]), 'job_postings': job_postings}
    context = ""
    lambda_handler(event, context)
