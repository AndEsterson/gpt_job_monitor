import re
import requests
import datetime
import send_email
from bs4 import BeautifulSoup
from openai import OpenAI

job_posting = """
We’re looking for an experienced Proteomics/Mass Spectrometry Technician to join the Proteomics Facility at King’s College London, Denmark Hill Campus.

The Proteomics Facility specialises in peptide and protein analysis using mass spectrometry. It offers a wide range of services, from protein identification to post-translational modification analysis and quantification.

Our mission is to advance biological understanding and train the next generation of researchers in this vital field.

The purpose of the role is to provide technical assistance and support to proteomic projects from King’s College London researchers and external organisations. This includes operation and maintenance of the Thermo Scientific Tribrid Orbitrap mass spectrometer, sample preparation, data analysis and management, report writing and day-to-day operation of general lab equipment in the facility, under the guidance of the Facility Manager and Deputy Manager.

The successful candidate will deliver support in an organised, timely and efficient manner and be able to manage and prioritise their own workload. Strong commutation skills are a key aspect of the role, and the successful candidate will need to communicate effectively with clients, colleagues, and external partners.

This role offers opportunities for development and growth and the facility is committed to supporting staff to reach their career aspirations.

This post will be offered on an indefinite contract.

This is a full-time post - 100% full time equivalent.

Skills, knowledge, and experience

Essential criteria

    BSc/MSc, or equivalent experience in Chemistry, Biochemistry, or related subject with practical experience of working in a proteomics laboratory in an academic or industry setting.
    Excellent technical knowledge of Orbitrap Tribrid MS equipment and nano liquid chromatography or similar high-end mass spectrometers.
    Excellent knowledge of mass spectrometry data analysis, data interpretation and computational methods using software such as Proteome Discoverer, MaxQuant, Peaks Scaffold etc.
    Experience in the preparation of biological samples to a high standard.
    Experience of calibration and troubleshooting technical problems with MS and LC & UHPLC chromatography systems.
    Excellent planning and organisational skills, with the ability to manage competing priorities.
    Detailed and focused approach, ability to record and manage data accurately, and in accordance with GDPR and legislation requirements.
    Strong commutations skills and ability to communicate effectively with colleagues, clients, and industry partners.
    Good understanding of Health and Safety practices in a laboratory setting and knowledge of legal requirements and relevant policies, including the Human Tissue Authority Legislation and COSHH.

Desirable criteria

    Familiarity or expertise in R, python, or similar languages.
    Able to demonstrate broad biology and proteomic skills.

"""

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
    client = OpenAI(api_key=params['api_key'])
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

if __name__ == "__main__":
    email_source = "gpt.andrew.esterson@gmail.com"
    email_destination = "andrewesterson1@gmail.com"
    params = get_parameters()
    jobs = get_job_data(params)
    filter_jobs(jobs)
    send_email.send_email(params['email_source'], params['email_destination'], 
                [job for job in jobs if job['important']],
                [job for job in jobs if not job['important']])

