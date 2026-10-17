from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
import requests

USER_AGENT = "CSS576EducationalBot/1.0 (css576.cyber.dataset@gmail.com)"


def check_robots(url):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    response = requests.get(
        robots_url,
        headers={"User-Agent": USER_AGENT},
        timeout=10
    )

    print("Robots status:", response.status_code)

    # Do not interpret a rejected request as permission
    if response.status_code != 200:
        print("Could not retrieve robots.txt successfully")
        return False

    robot = RobotFileParser()
    robot.parse(response.text.splitlines())

    return robot.can_fetch(USER_AGENT, url)


url = "https://www.wikipedia.org/"

allowed = check_robots(url)

print("Crawling permitted by robots.txt:", allowed)


# import requests

# url = "https://www.wikipedia.org/robots.txt"

# response = requests.get(url, timeout=10)

# print("Status code:", response.status_code)
# print("Final URL:", response.url)
# print("Content:")
# print(response.text[:1000])