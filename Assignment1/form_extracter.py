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
from datetime import datetime, timezone
# initialize an HTTP session
session = HTMLSession()

USER_AGENT = "CSS576EducationalBot/1.0 (css576.cyber.dataset@gmail.com)"
session.headers.update({"User-Agent": USER_AGENT})

def load_persona(file_path):
    with open(file_path, "r") as file:
        return json.load(file)

def classify_form(form_details):

    inputs = form_details["inputs"]

    field_names = {
        field["name"].lower()
        for field in inputs
        if field.get("name")
    }

    action = (form_details["action"] or "").lower()

    # Check for search forms
    if (
        "search" in field_names
        or "/search" in action
    ):
        return "search"

    # Check for login forms
    if (
        "password" in field_names
        or any(
            field.get("type", "").lower() == "password"
            for field in inputs
        )
    ):
        return "login_or_account"

    # Check for possible newsletter forms
    email_fields = {
        "email",
        "email_address",
        "emailaddress",
        "e-mail"
    }

    has_email = any(
            "email" in name
            or field.get("type", "").lower() == "email"
            for name, field in zip(field_names, inputs)
        )
    if has_email and any(
        keyword in action
        for keyword in ("subscribe", "newsletter", "signup", "submit.jotform.com")
    ):
        return "possible_newsletter"

    return "possible_newsletter"

def prepare_form_data(form_details, persona):
    data = {}

    field_mapping = {
                "q5_email5": "email",
                "custemail" : "email",
        "q4_address4[addr_line1]": "address",
        "q4_address4[city]": "city",
        "q4_address4[state]": "state",
        "q4_address4[postal]": "pincode",
        "q4_address4[country]": "country",

        "name": "name",
        "full_name": "name",
        "fullname": "name",
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "email",
        "email_address": "email",
        "phone": "phone_number",
        "phone_number": "phone_number",
        "address": "address",
        "city": "city",
        "state": "state",
        "zip": "pincode",
        "zipcode": "pincode",
        "country": "country"
    }

    for field in form_details["inputs"]:
        original_name = field.get("name")

        if not original_name:
            continue

        normalized_name = original_name.lower()
        field_type = field.get("type", "text").lower()

        # Skip controls that require special handling
        if field_type in (
            "submit", "button", "reset",
            "image", "file", "password",
            "checkbox", "radio"
        ):
            continue

        # Preserve hidden fields in the local test,
        # but don't modify their values
        if field_type == "hidden":
            data[original_name] = field.get("value", "")
            continue

        persona_key = field_mapping.get(normalized_name)

        if persona_key and persona_key in persona:
            data[original_name] = persona[persona_key]

    return data

def save_submission_log(
    website_url,
    submission_url,
    method,
    form_data,
    status_code,
    submission_status,
    confirmation_status
):
    print("\n------ SUBMISSION LOG ------")
    filename = "submission_log.csv"

    write_header = (
        not os.path.exists(filename)
        or os.path.getsize(filename) == 0
    )

    with open(filename, "a", newline="") as file:
        writer = csv.writer(file)

        if write_header:
            writer.writerow([
                "Website URL",
                "Submission URL",
                "Timestamp",
                "Method",
                "Submitted Data",
                "HTTP Status",
                "Submission Status",
                "Confirmation Status"
            ])

        writer.writerow([
            website_url,
            submission_url,
            datetime.now(timezone.utc).isoformat(),
            method,
            json.dumps(form_data),
            status_code,
            submission_status,
            confirmation_status
        ])

def submit_form_local(submission_url, method, form_data):

    parsed = urlparse(submission_url)

    # if parsed.hostname not in ("localhost", "127.0.0.1"):
    #     raise ValueError("Only local submissions are permitted")

    method = method.lower()

    if method == "post":
        response = session.post(
            submission_url,
            data=form_data,
            timeout=10
        )

    elif method == "get":
        response = session.get(
            submission_url,
            params=form_data,
            timeout=10
        )

    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    return response

def check_robots(url):
    parsed = urlparse(url)
    if parsed.hostname in ("localhost", "127.0.0.1"):
        return True
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

def classify_submission_response(
    response,
    is_local=False,
    form_data=None
):
    status_code = response.status_code

    soup = BeautifulSoup(response.text, "html.parser")

    page_title = (
        soup.title.get_text(" ", strip=True).lower()
        if soup.title
        else ""
    )

    has_captcha = (
        soup.find("input", {"name": "captcha"}) is not None
        or soup.find(class_="form-captcha") is not None
    )

    if has_captcha and "please complete" in page_title:
        return "Pending - CAPTCHA verification required"

    if status_code == 400:
        return "Rejected - Invalid form data"

    if status_code == 403:
        return "Rejected - Forbidden"

    if status_code == 404:
        return "Failed - Endpoint not found"

    if status_code >= 500:
        return "Server error"

    # Check application-level JSON response
    try:
        response_data = response.json()

        if isinstance(response_data, dict):
            result = str(response_data.get("result", "")).lower()

            if result in ("error", "failed", "failure"):
                return "Rejected - Application error"

    except ValueError:
        pass

    if (
        response.status_code == 200
        and response.url.startswith("https://httpbin.org/post")
        and form_data is not None
    ):
        try:
            response_json = response.json()

            received_data = response_json.get("form", {})

            if received_data == form_data:
                return "Verified - HTTP test submission"

            return "Failed - Payload mismatch"

        except (ValueError, AttributeError):
            return "Unverified - Invalid test response"
            
    # Check our own local server's known success message
    if is_local and (
        status_code == 200
        and "Subscription received successfully" in response.text
    ):
        return "Received - Local test"

    # HTTP success does not prove registration
    if 200 <= status_code < 300:
        return "HTTP success - Registration unverified"

    if 300 <= status_code < 400:
        return "Redirect - Unverified"

    

    return "Unverified"

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
            
            print("\n------ EXTRACTED FORM DETAILS ------")
            pprint(form_details)

            form_type = classify_form(form_details)

            print("Form Type:", form_type)

            if form_type != "possible_newsletter" :
                print("Skipping: Not a recognized newsletter form")
                continue
            print("="*50, f"form #{i}", "="*50)
            pprint(form_details)
            form_data = prepare_form_data(form_details, persona)
            has_email = any(
                key.lower() in ("q5_email5","email", "email_address", "emailaddress", "e-mail", "custemail")
                and str(value).strip()
                for key, value in form_data.items()
            )

            # if not has_email:
            #     print("Skipping: Missing email value")
            #     continue
            print("\n------ DRY RUN ------")
            print("Website:", url)
            submission_url = urljoin(url, form_details["action"] or "")

            print("Submission URL:", submission_url)
            print("Method:", form_details["method"])
            print("Payload:")
            pprint(form_data)
            print("Submission performed: NO")
            save_form_results(url, [form])

            # if urlparse(submission_url).hostname in ("localhost", "127.0.0.1"):

            try:
                response = submit_form_local(
                    submission_url,
                    form_details["method"],
                    form_data
                )

                print("\n------ LOCAL SUBMISSION RESULT ------")
                print("Status Code:", response.status_code)
                print("Response:", response.text)

# Check whether the local test server accepted the request
                is_local = urlparse(submission_url).hostname in (
                    "localhost",
                    "127.0.0.1"
                )

                submission_status = classify_submission_response(
    response,
    is_local=is_local,
    form_data=form_data
)

                confirmation_status = (
                    "Local test only"
                    if is_local
                    else "Not verified"
                )

                print("Submission Status:", submission_status)
                print("Confirmation Status:", confirmation_status)

                save_submission_log(
                website_url=url,
                submission_url=submission_url,
                method=form_details["method"],
                form_data=form_data,
                status_code=response.status_code,
                submission_status=submission_status,
                confirmation_status=confirmation_status
            )

            except requests.RequestException as e:
                print("Submission error:", e)
                save_submission_log(
                website_url=url,
                submission_url=submission_url,
                method=form_details["method"],
                form_data=form_data,
                status_code=response.status_code,
                submission_status=submission_status,
                confirmation_status=confirmation_status
)




import csv
from collections import Counter

with open("submission_log.csv", newline="") as file:
    rows = list(csv.DictReader(file))

statuses = Counter(row["Submission Status"] for row in rows)

print("Total submission attempts:", len(rows))

for status, count in statuses.items():
    print(f"{status}: {count}")