from bs4 import BeautifulSoup
from requests_html import HTMLSession
from pprint import pprint
import csv
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
import requests
import os
from urllib.parse import urljoin
import json
# initialize an HTTP session
session = HTMLSession()

USER_AGENT = "CSS576EducationalBot/1.0 (css576.cyber.dataset@gmail.com)"
session.headers.update({"User-Agent": USER_AGENT})

def load_persona(file_path):
    with open(file_path, "r") as file:
        return json.load(file)

def perpare_form_data(form_details, persona):
    data = {}
    for input_field in form_details["inputs"]:
        field_name1 = input_field.get("name")
        
        if not field_name1:
            continue  # Skip inputs without a name attribute

        field_name = field_name1.lower()
        # Use persona data if available, otherwise use default value
        if field_name in persona:
            data[field_name] = persona[field_name]
        else:
            data[field_name] = input_field.get("value", "")
    return data

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

# read seed URLs from a CSV file
def read_seed_urls(csv_file):
    urls = []

    with open(csv_file, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            url = row["url"].strip()
            if url:
                urls.append(url)

    return urls

def save_form_results(url, forms):
    filename = "extracted_forms.csv"

    write_header = (
        not os.path.exists(filename)
        or os.path.getsize(filename) == 0
    )

    with open(filename, "a", newline="") as file:
        writer = csv.writer(file)

        if write_header:
            writer.writerow([
                "URL", "Form Action",
                "Form Method", "Number of Inputs"
            ])

        for form in forms:
            details = get_form_details(form)

            writer.writerow([
                url,
                urljoin(url, details["action"] or ""),
                details["method"],
                len(details["inputs"])
            ])

# modified function get_all_forms(url) to read from a local file instead of making an HTTP request
def get_all_forms_local_file(file_path):
    with open(file_path, "r") as file:
        html = file.read()
    soup = BeautifulSoup(html, "html.parser")
    return soup.find_all("form")

def get_all_forms(url):
    """Returns all form tags found on a web page's `url` """
    # GET request
    res = session.get(url)
    # for javascript driven website
    # res.html.render()
    soup = BeautifulSoup(res.html.html, "html.parser")
    return soup.find_all("form")


def get_form_details(form):
    """Returns the HTML details of a form,
    including action, method and list of form controls (inputs, etc)"""
    details = {}
    # get the form action (requested URL)
    action = form.get("action")
    if action:
        action = action
    # get the form method (POST, GET, DELETE, etc)
    # if not specified, GET is the default in HTML
    method = form.get("method", "get")
    # get all form inputs
    inputs = []
    for input_tag in form.find_all("input"):
        # get type of input form control
        input_type = input_tag.get("type", "text")
        # get name attribute
        input_name = input_tag.get("name")
        # get the default value of that input tag
        input_value =input_tag.get("value", "")
        # add everything to that list
        inputs.append({"type": input_type, "name": input_name, "value": input_value})
    for select in form.find_all("select"):
        # get the name attribute
        select_name = select.get("name")
        # set the type as select
        select_type = "select"
        select_options = []
        # the default select value
        select_default_value = ""
        # iterate over options and get the value of each
        for select_option in select.find_all("option"):
            # get the option value used to submit the form
            option_value = select_option.get("value")
            if option_value:
                select_options.append(option_value)
                if select_option.has_attr("selected"):
                    # if 'selected' attribute is set, set this option as default    
                    select_default_value = option_value
        if not select_default_value and select_options:
            # if the default is not set, and there are options, take the first option as default
            select_default_value = select_options[0]
        # add the select to the inputs list
        inputs.append({"type": select_type, "name": select_name, "values": select_options, "value": select_default_value})
    for textarea in form.find_all("textarea"):
        # get the name attribute
        textarea_name = textarea.get("name")
        # set the type as textarea
        textarea_type = "textarea"
        # get the textarea value
        textarea_value = textarea.get_text()
        # add the textarea to the inputs list
        inputs.append({"type": textarea_type, "name": textarea_name, "value": textarea_value})
        
    # put everything to the resulting dictionary
    details["action"] = action
    details["method"] = method
    details["inputs"] = inputs
    return details


if __name__ == "__main__":
    import sys
    # # get URL from the command line
    # url = sys.argv[1]
    # # get all form tags
    # forms = get_all_forms(url)

    #get all form tags from a local file
    # forms = get_all_forms_local_file("sample.html")
    # # iteratte over forms
    # for i, form in enumerate(forms, start=1):
    #     form_details = get_form_details(form)
    #     print("="*50, f"form #{i}", "="*50)
    #     pprint(form_details)

    urls = read_seed_urls("seeds.csv")
    persona = load_persona("persona.json")


    for url in urls:
        allowed = check_robots(url)
        if not allowed:
            print(f"Crawling not permitted by robots.txt for: {url}")
            continue
        print(f"Extracting forms from: {url}")
        forms = get_all_forms(url)
        for i, form in enumerate(forms, start=1):
            form_details = get_form_details(form)
            print("="*50, f"form #{i}", "="*50)
            pprint(form_details)
            form_data = perpare_form_data(form_details, persona)
            print("\n------ DRY RUN ------")
            print("Website:", url)
            submission_url = urljoin(url, form_details["action"] or "")

            print("Submission URL:", submission_url)
            print("Method:", form_details["method"])
            print("Payload:")
            pprint(form_data)
            print("Submission performed: NO")
            save_form_results(url, [form])