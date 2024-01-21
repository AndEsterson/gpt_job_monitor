import re
import requests
import datetime
from bs4 import BeautifulSoup
from openai import OpenAI

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
            raise Exception(f"job description text missing for {url}")
        
        placed_on_th = soup.find('th', string='Placed On:')
        if placed_on_th:
            placed_on_date_str = placed_on_th.find_next('td').text.strip()
            placed_on_date = datetime.datetime.strptime(placed_on_date_str, '%dth %B %Y').date()
            job_specifics.update({'placed_on': placed_on_date})
        else:
            raise Exception(f"placed on date not found for {url}")
        
        return job_specifics
    else:
        raise Exception(f"request errored for {url}, {response.status_code}")
        
def get_gpt_response(job_description):
    client = OpenAI()
    response = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[
        {"role": "system", "content": """
        You are a helpful assistant. You give brief answers ranking the relevance of job postings for a person with the following description:
        I have a master's degree in physics, with a project involving computational neuroscience. Since graduating,
        I have ~18 months of experience as a DevOps engineer, working with Python, Bash, AWS, terraform, kubernetes, git, postgreSQL.
        I do not hold a PhD, and don't have experience lecturing or doing experimental lab work.
        I am looking for jobs that involve programming, especially cloud hosting or CI/CD, bonus points for roles with an ethical value.
        You give a brief description of the benefits of the job and an overall score out of 10 based on value and relevancy of the person's experience
        """},
        {"role": "user", "content": example_under_qualified_job_posting},
        {"role": "assistant", "content": example_under_qualified_job_response},
        {"role": "user", "content": example_qualified_job_posting},
        {"role": "assistant", "content": example_qualified_job_response},
        {"role": "user", "content": job_posting},
        ]
    )
    return response.choices[0].message.content

def extract_gpt_rating(gpt_response):
    ratings = re.findall("\d+\/10", gpt_response)
    return sum([int(rating.split('/')[0]) for rating in ratings])/len(ratings)

def get_job_data():
    url = 'https://www.jobs.ac.uk/search/?location=London%2C+UK&locationCoords%5B0%5D=51.5072178%2C-0.1275862&locality%5B0%5D=London&administrativeAreaLevel1%5B0%5D=England&administrativeAreaLevel2%5B0%5D=Greater+London&country%5B0%5D=United+Kingdom&country%5B1%5D=GB&distance=0&placeId=ChIJdd4hrwug2EcRmSrV3Vo6llI&activeFacet=nonAcademicDisciplineFacet&sortOrder=1&pageSize=25&startIndex=1'
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        job_entries = soup.find_all('a', href=True)
        jobs = []
        for entry in job_entries:
            job_name = entry.get_text(strip=True)
            job_link = "https://www.jobs.ac.uk" + entry['href']
            if job_link.startswith("https://www.jobs.ac.uk/job/"):
                jobs.append({'name': job_name, 'link': job_link})

        for job in jobs:
            job.update(get_job_specifics(job['link']))
            if job['placed_on'] == datetime.date.today():
                job.update({'gpt_response': get_gpt_response(job['description'])})
                job.update({'gpt_rating': extract_gpt_rating(job['gpt_response'])})
        jobs = sorted(jobs, key=lambda j: j.get("gpt_rating", 0), reverse=True)
        return jobs
    else:
        raise Exception(f"Failed to retrieve the webpage. Status Code: {response.status_code}")

def output_filtered_jobs():
    for job in jobs:
        if job.get("gpt_rating", 0) > 6:
            print(job['name'])
            print(job['link'])
            print(job['gpt_response'])

if __name__ == "__main__":
    jobs = get_job_data()
    output_filtered_jobs()

