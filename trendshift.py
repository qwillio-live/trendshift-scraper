import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
import tls_client
import json
from bs4 import BeautifulSoup
from db import database, Language, Repository, Ranking, Config
from loguru import logger

# Environment variables
DELAY_IN_SECONDS = int(os.getenv('DELAY', 2))
ERROR_DELAY_IN_SECONDS = int(os.getenv('ERRORDELAY', 60))
MAX_ID = int(os.getenv('MAXID', 12000))
MAX_RETRY = int(os.getenv('MAXERRORNUMBER', 5))
LAST_RUN_CHECK = int(os.getenv('LASTRUNCHECK', 48))
PROXY_URL = os.getenv('PROXY', None)
NOTIFICATION_URL = os.getenv('NOTIFICATIONURL', None)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', None)
DISABLE_CRON = os.getenv('DISABLECRON', False)

if "--trigger-manual" in sys.argv:
    logger.info(f"Script Started Manually Ignoring Disable Cron Value: {DISABLE_CRON}")
else:
    if DISABLE_CRON is True or str(DISABLE_CRON).lower() == "true":
        logger.info("Cron is disabled")
        exit()

# current path from os
current_script_path = os.path.dirname(os.path.realpath(__file__))
logs_path = os.path.join(current_script_path, 'logs')
if not os.path.exists(logs_path):
    os.makedirs(logs_path)
log_file_path = os.path.join(logs_path, 'logs.txt')

# Logger Configuration
logger.remove()
logger.add(
    log_file_path,
    format="{time:YYYY-MM-DD at HH:mm:ss}\t{level}\t{message}",
    backtrace=False,
    diagnose=False,
    rotation="14 days",
)
logger.add(sys.stdout, backtrace=False, diagnose=False, colorize=True, format="<level>{message}</level>")

# Database Connection
database.connect()

# Request Session
session = tls_client.Session(
    client_identifier='chrome_120',
    random_tls_extension_order=True,
)

# https://api.ipify.org
# logger.success(session.get('https://api.ipify.org').text)

useragents = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.324 YaApp_Android/24.19.1 YaSearchBrowser/24.19.1 BroPP/1.0 SA/3 Safari/537.36",
    "Mozilla/5.0 (Android 11.0.0; TECNO KG5n) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Chrome/120.0.6099.210 Not_A Brand/8 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.234 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.234 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; WayDroid x86_64 Device Build/RQ3A.211001.001) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.230 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.324 Safari/537.36"]

session.headers.update({
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "priority": "u=0, i",
})

if PROXY_URL and PROXY_URL != "None":
    logger.info(f"Using Proxy: {PROXY_URL}")
    session.proxies = {
        "http": PROXY_URL,
        "https": PROXY_URL
    }

unit_multipliers = {
    'k': 1000,
    'm': 1000000,
    'b': 1000000000,
}


def last_checked_id_save(trendshift_id: int):
    config = Config.select().where(Config.key == 'last_checked_id').first()
    if config:
        config.value = str(trendshift_id)
        config.expire = datetime.now() + timedelta(hours=LAST_RUN_CHECK)
        config.save()
    else:
        Config.create(
            key='last_checked_id',
            value=str(trendshift_id),
            expire=datetime.now() + timedelta(hours=LAST_RUN_CHECK)
        )


def convert_to_int(temp_str):
    if temp_str[-1] in unit_multipliers:
        unit = temp_str[-1]
        number = float(temp_str[:-1]) * unit_multipliers[unit]
    else:
        number = float(temp_str)

    return int(number)


# Send Notification
def send_notification(message: str):
    if NOTIFICATION_URL and NOTIFICATION_URL != "None":
        try:
            notification = session.post(NOTIFICATION_URL, data=message, headers={"Content-Type": "text/plain"})
            logger.info(f"Notification Sent: {notification.text}")
        except Exception as e:
            logger.error(f"Error in sending notification: {e}")


def get_starts_commit(github_link: str) -> dict | None:
    try:
        username = github_link.split("/")[-2]
        repo = github_link.split("/")[-1]
        query = f"""
            {{
                repository(owner: "{username}", name: "{repo}") {{
                    stargazerCount
                    createdAt
                    repositoryTopics(first: 100, after: null) {{
                        edges {{
                            node {{
                                topic {{
                                    name
                                }}
                            }}
                        }}
                    }}
                    defaultBranchRef {{
                        target {{
                            ... on Commit {{
                                history(first: 1) {{
                                    edges {{
                                        node {{
                                            committedDate
                                            message
                                            author {{
                                                name
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
            """

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }

        response = session.post("https://api.github.com/graphql", json={"query": query}, headers=headers)
        if response.status_code != 200:
            return None
        if "NOT_FOUND" in response.text:
            return {
                "stars": -1,
                "last_commit": None,
                "created_at": None,
                "topics": "[]"
            }
        response_json = response.json()
        stars = response_json["data"]["repository"]["stargazerCount"]
        created_at = response_json["data"]["repository"]["createdAt"]
        created_at = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
        last_commit = response_json["data"]["repository"]["defaultBranchRef"]["target"]["history"]["edges"][0]["node"][
            "committedDate"]
        last_commit = datetime.strptime(last_commit, '%Y-%m-%dT%H:%M:%SZ')
        topics=[]
        for topic in response_json["data"]["repository"]["repositoryTopics"]["edges"]:
            topics.append(topic["node"]["topic"]["name"])

        return {
            "stars": stars,
            "last_commit": last_commit.strftime('%Y-%m-%d %H:%M:%S'),
            "created_at": created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "topics": json.dumps(topics)
        }
    except Exception as e:
        logger.error(f"Error in getting starts and commit: {e}")
        return None


# Get data from Trendshift
def get_data(trendshift_id: int) -> dict | None:
    url = f'https://trendshift.io/repositories/{trendshift_id}'
    try:
        session.cookies.clear()
        session.headers.update({
            "User-Agent": random.choice(useragents),
        })
        response = session.get(url)
        if response.status_code != 200:
            return None
        name, language_text, github_link, website_link, description, forks = None, "No Language", None, None, None, 0
        trending = []
        soup = BeautifulSoup(response.text, 'html.parser')
        name_and_language_object = soup.find('div',
                                             {
                                                 'class': 'flex items-center text-indigo-400 text-lg justify-between mb-1'})
        if name_and_language_object:
            name_and_language_divs = name_and_language_object.find_all('div')
            if name_and_language_divs:
                name = name_and_language_divs[0].text.strip()
                if len(name_and_language_divs) > 1:
                    language_text = name_and_language_divs[1].text.strip()
                    if language_text == "":
                        language_text = "No Language"

        github_object = soup.find('a', string='Visit GitHub')
        if github_object:
            github_link = github_object['href']

        website_object = soup.find('a', string='Website')
        if website_object:
            website_link = website_object['href']

        description_object = soup.find('div', {'class': 'text-sm text-gray-500'})
        if description_object:
            description = description_object.text.strip()
            if description == "":
                description = None

        # star_path_object = soup.find('path', d=lambda x: x and x.startswith('M8 .25a.75.75 0 0 1 .6'))
        # if star_path_object:
        #     svg_object = star_path_object.find_parent('svg')
        #     if svg_object:
        #         start_div_object = svg_object.find_parent('div')
        #         if start_div_object:
        #             try:
        #                 stars = convert_to_int(start_div_object.text.strip())
        #             except Exception as e:
        #                 logger.error(f"Error in converting stars: {e}")

        forks_path_object = soup.find('path', d=lambda x: x and x.startswith('M5 5.372v.878c0 .414.33'))
        if forks_path_object:
            svg_object = forks_path_object.find_parent('svg')
            if svg_object:
                forks_div_object = svg_object.find_parent('div')
                if forks_div_object:
                    try:
                        forks = convert_to_int(forks_div_object.text.strip())
                    except Exception as e:
                        logger.error(f"Error in converting forks: {e}")

        trending_data_regex = re.compile(r'trendings\\":\[(.*?)}]')
        trending_data_match = trending_data_regex.findall(response.text)
        if trending_data_match:
            trending_data = json.loads('{"trendings":[' + trending_data_match[0].replace('\\', '') + '}]}')
            trending = trending_data['trendings']

        stars_commit_data = get_starts_commit(github_link)
        if not stars_commit_data:
            stars_commit_data = {
                "stars": 0,
                "last_commit": None,
                "created_at": None,
                "topics": "[]"
            }

        return {
            "name": name,
            "language": language_text,
            "github_link": github_link,
            "website_link": website_link,
            "description": description,
            "stars": stars_commit_data["stars"],
            "forks": forks,
            "trending": trending,
            "last_commit": stars_commit_data["last_commit"],
            "started": stars_commit_data["created_at"],
            "topics": stars_commit_data["topics"]
        }
    except Exception as e:
        logger.error(f"Error in getting data: {e}")
        return None


start_id = 1
last_checked_id_object = Config.select().where(Config.key == 'last_checked_id').first()
if last_checked_id_object:
    if last_checked_id_object.expire > datetime.now():
        start_id = int(last_checked_id_object.value)
    else:
        last_checked_id_object.delete_instance()

error_count = 0
no_language, _ = Language.get_or_create(name="No Language")
last_id = 0
for i in range(start_id, MAX_ID + 1):
    if error_count >= MAX_RETRY:
        logger.error(f"MAX ERROR COUNT REACHED: {error_count}")
        send_notification(f"MAX ERROR COUNT REACHED: {error_count}, Stopping the Trendshift Scraper at ID: {i}")
        break
    logger.info(f"ID: {i}")
    is_error_delay = False
    try:
        is_error_delay = False
        repository = Repository.select().where(Repository.trendshift_id == i).first()
        if repository and repository.updated_at > (
                datetime.now() - timedelta(hours=LAST_RUN_CHECK)) and repository.error == 0:
            logger.info(f"Skipping Cause of Last Run Check: {repository.updated_at}")
            continue
        data = get_data(i)
        if not data:
            error_count += 1
            logger.error(f"Data not found for ID: {i}")
            if repository:
                repository.error = 1
                repository.updated_at = datetime.now()
                repository.save()
            else:
                Repository.create(
                    name="N/A",
                    github="N/A",
                    trendshift_id=i,
                    error=1,
                    lang=no_language
                )
            continue
        error_count = 0
        language, _ = Language.get_or_create(name=data['language'])
        if repository:
            repository.name = data['name']
            repository.github = data['github_link']
            repository.website = data['website_link']
            repository.description = data['description']
            repository.stars = data['stars'] if data['stars'] != 0 else repository.stars
            repository.forks = data['forks']
            repository.lang = language
            repository.last_commit = data['last_commit'] if data['last_commit'] else repository.last_commit
            repository.started = data['started'] if data['started'] else repository.started
            repository.topics = data['topics'] if data['topics'] != "[]" else repository.topics
            repository.updated_at = datetime.now()
            repository.save()

            for trend in data['trending']:
                date = datetime.strptime(trend["trend_date"].split('T')[0], '%Y-%m-%d').date()
                if trend["trending_language"]:
                    ranking = Ranking.select().where(Ranking.repository == repository, Ranking.lang == language,
                                                     Ranking.rank_date == date).first()
                    if ranking:
                        ranking.rank = trend["rank"]
                        ranking.save()
                    else:
                        Ranking.create(
                            repository=repository,
                            lang_id=language,
                            rank=trend["rank"],
                            rank_date=date
                        )
                else:
                    ranking = Ranking.select().where(Ranking.repository == repository, Ranking.lang == no_language,
                                                     Ranking.rank_date == date).first()
                    if ranking:
                        ranking.rank = trend["rank"]
                        ranking.save()
                    else:
                        Ranking.create(
                            repository=repository,
                            rank=trend["rank"],
                            rank_date=date,
                            lang_id=no_language
                        )

        else:
            repository = Repository.create(
                name=data['name'],
                github=data['github_link'],
                website=data['website_link'],
                description=data['description'],
                stars=data['stars'],
                forks=data['forks'],
                lang=language,
                trendshift_id=i,
                last_commit=data['last_commit'],
                started=data['started'],
                topics=data['topics'],
                error=0
            )

            for trend in data['trending']:
                if trend["trending_language"]:
                    ranking = Ranking.create(
                        repository=repository,
                        lang_id=language,
                        rank=trend["rank"],
                        rank_date=datetime.strptime(trend["trend_date"].split('T')[0], '%Y-%m-%d').date()
                    )
                else:
                    ranking = Ranking.create(
                        repository=repository,
                        rank=trend["rank"],
                        rank_date=datetime.strptime(trend["trend_date"].split('T')[0], '%Y-%m-%d').date(),
                        lang_id=no_language
                    )
    except Exception as err:
        error_count += 1
        logger.error(f"Error in getting data: {err}")
        time.sleep(ERROR_DELAY_IN_SECONDS)
        is_error_delay = True
        continue
    finally:
        last_id = i
        last_checked_id_save(i)
        if not is_error_delay:
            time.sleep(DELAY_IN_SECONDS)

if error_count < MAX_RETRY:
    send_notification(f"Trendshift Scraper Completed at Last ID: {last_id}")
