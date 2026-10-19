# Assignment 1 – Security Data Collection

**Course:** CSS 576 – Cybersecurity and AI  
**University:** University of Washington Bothell

## Objective

Develop a spam crawler and collect network traffic data for subsequent cybersecurity analysis.

## Part A – Spam Crawler Data Collection

## Assignment Milestones

| Milestone | What I Did |
|-----------|------------|
| **Crawler built and tested locally** | Created a local HTML signup form and Python HTTP server; tested accepted and rejected requests. |
| **Invent a persona** | Created a fictional test profile in `persona.json`, including a test name, email, and address information. |
| **Inspect a form by hand before automation** | Examined HTML form actions, methods, field names, types, required data, and hidden fields; later reviewed extracted forms and their payloads before interpreting results. |
| **Build real seeds with judgment** | Used `seeds.csv` to curate candidate newsletter pages and test forms rather than indiscriminately crawling arbitrary pages. |
| **Dry run → review → real run** | Printed each destination and proposed payload before testing submissions; reviewed the server responses and confirmation evidence separately. |
| **Deliverable 1** | Submitted crawler code, this explanation, observed results, limitations, and proposed improvements. |

## Project Files

| File | Purpose |
|---|---|
| `form_extracter.py` | Main crawler: seed loading, robots checking, HTML extraction, form classification, payload preparation, submission, and logging. The spelling is preserved to match the existing file. |
| `seeds.csv` | CSV of website URLs with a `url` header. |
| `persona.json` | Fictional test data used to populate recognized form fields. |
| `sample.html` | Local subscription form for testing. |
| `test_server.py` | Local HTTP server used to receive submissions and return validation responses. |
| `extracted_forms.csv` | Extracted URL, resolved action, method, and number of controls. |
| `submission_log.csv` | Timestamped submission attempts, payloads, HTTP codes, classification, and confirmation status. |

**How the crawler works**

1. Load configuration. read_seed_urls("seeds.csv") uses csv.DictReader to read URLs. load_persona("persona.json") loads the fictional test identity using json.load.
2. Check whether the page can be crawled. check_robots() fetches the site's /robots.txt with an identifying user agent and uses RobotFileParser.can_fetch(). Localhost is handled as a local test. A failed robots fetch is treated conservatively and skipped. Robots permission does not itself authorize form submission.
3. Fetch and parse HTML. get_all_forms() uses requests_html.HTMLSession to fetch page HTML and BeautifulSoup to identify <form> elements. It does not currently execute JavaScript; embedded or browser-generated forms may be missed.
4. Extract the form structure. get_form_details() collects the form action, method (default GET), text/input controls, select choices, and textarea values. urljoin() converts relative or protocol-relative actions to absolute submission URLs.
5. Classify the form. classify_form() attempts to distinguish searches, account/login forms, and potential subscription forms using field names, types, and action URLs. Current limitation: its fallback classifies unknown forms as possible_newsletter, so this remains a heuristic requiring manual review.
6. Build the sample payload. prepare_form_data() maps known HTML names to values from persona.json while preserving the original field names and their capitalization. It handles known aliases such as Jotform's q5_email5 and HTTPBin's custemail. It preserves hidden inputs but currently skips checkbox, radio, password, file, and submit controls. Unmapped fields may remain absent.
7. Display a dry run. The program prints the page, resolved destination, HTTP method, and prepared data before an actual request.
8. Send an HTTP request. The current submit_form_local() function issues a POST or GET and returns the HTTP response. Despite the function name, the latest code has its localhost-only restriction commented out. External requests should only be made to endpoints owned or explicitly approved for automated testing; third-party newsletter forms should otherwise be tested in read-only mode or submitted through their ordinary user interface.
9. Interpret the response. classify_submission_response() separates invalid requests (e.g., HTTP 400), forbidden requests (403), missing endpoints (404), server errors (5xx), JSON application errors, CAPTCHA challenge pages, locally confirmed test-server responses, and HTTPBin echo responses. Otherwise an HTTP 2xx result remains unverified.
10. Save results. save_form_results() appends form metadata to extracted_forms.csv. save_submission_log() appends submission details and a UTC timestamp to submission_log.csv. A final Counter summarizes all rows currently in the log.

## Workflow
seeds.csv + persona.json
          |
          v
     check robots.txt
          |
      permitted?
      /        \
    no          yes
   skip          |
                 v
           fetch page HTML
                 |
            extract forms
                 |
            classify forms
                 |
          prepare sample data
                 |
             print dry run
                 |
           approved test only
                 |
           send GET or POST
                 |
        inspect HTTP + body
                 |
     extracted_forms.csv and
         submission_log.csv

## Development and testing timeline

1. **Built the initial extractor**

I started by using requests_html and BeautifulSoup to download pages and locate HTML forms. I added a function to read form metadata and inputs, including text boxes, dropdowns, and text areas. Initially, I tested simple local/sample forms to check whether form actions, HTTP methods, and input fields were extracted correctly.
**Issues encountered:** Some inputs had no name attribute, causing lookup problems when their names were processed as strings. The extractor was updated to skip unnamed inputs. Some dropdowns did not have an explicitly selected option, so a default-option fallback was added. The code also needed to preserve the original action string and resolve relative action paths using urljoin().

2. **Created the persona and mapped inputs**

I created persona.json with fictional name, email, street address, city, state, postal code, country, and phone data. The crawler mapped recognized form fields to this persona instead of entering data manually for every test.
**Issue encountered:** An earlier version lowercased both the lookup key and the output key. This changed HTML field names such as EMAIL to email, which may not be accepted by case-sensitive form handlers. I fixed this by using a lowercase version only for lookup and preserving the original HTML name in the outgoing payload. Other websites used different names (custemail on HTTPBin and q5_email5, q4_address4[...] on Jotform), requiring extra field aliases. These aliases remain site-specific and are not a universal mapping algorithm.

3. **Built and validated the local server**

I used sample.html and test_server.py to simulate a subscription form. The server received form data at /subscribe and returned a plain-text success message for accepted submissions. I tested both valid and malformed email inputs.
**Results:** Valid submissions received HTTP 200 and the message Subscription received successfully. An invalid test email (missing @) received HTTP 400. I changed the response logic to distinguish accepted local submissions from rejected form data. I also encountered an address/port-already-in-use condition when an old instance of the local server was still running, and resolved it by stopping the previous process.

4. **Added robots checks and curated URLs**

I added seeds.csv to manage a selected list of signup pages and public form-testing pages. I implemented robots.txt checks using RobotFileParser and a descriptive User-Agent.
**Issues encountered:** Some websites returned an HTTP 403 when their robots file was requested, and the crawler conservatively skipped them. Getting an HTTP 200 from robots.txt only establishes that the file was fetched; the crawler still uses can_fetch() to determine whether the requested page is permitted. It does not establish permission for creating accounts or registrations.

5. **Added the dry-run stage**

Before each candidate submission, the crawler printed the form URL, resolved action, method, and payload. This helped reveal incorrect field mapping, incomplete payloads, hidden fields, and irrelevant forms. It also made it possible to inspect a form before deciding whether an actual request was appropriate.
**Issue encountered: **TheFreeSite newsletter page contained both newsletter forms and a normal search form. The crawler initially attempted to process all forms, demonstrating the need to classify and deduplicate them. Some forms contained CAPTCHA-related or honeypot fields, which should not be bypassed or automatically filled.

6. **Tested real-world forms and HTTP responses**

| Test target | Observation | Conclusion |
|---|---|---|
| Local signup server (`http://localhost:8000`) | Valid POST returned HTTP 200 and a known local success message. Malformed email returned HTTP 400. | Local submission and rejection handling demonstrated. |
| TheFreeSite newsletter | Forms were extracted; an earlier response returned HTTP 200 alongside a JSON application error saying an email or phone number was required. Later HTTP 200 results were unverified. | HTTP 200 alone is not proof of newsletter registration; field-name preservation mattered. |
| TheFreeSite site search | `/search` returned HTTP 200 with a search-result page. | A normal search form is not a subscription. |
| Published Jotform owned for testing | Python POST returned HTTP 200 but the response page was titled `Please Complete` and displayed a CAPTCHA; no corresponding entry was found in the submissions dashboard. A manual browser submission did appear. | Automated request reached a verification challenge and did not complete a stored submission. |
| HTTPBin (`https://httpbin.org/forms/post` → `/post`) | HTTP 200 JSON response echoed the submitted `custemail` under `form`. | Verified that the external HTTP test server received and parsed the submitted field. This is **not** an actual subscription. |
| NASA JPL and Smithsonian newsletter pages | Crawler printed the page being inspected, but no extracted form output was observed. | Static HTML extraction did not find a form in these runs; JavaScript or embedded forms are possible reasons, not confirmed causes. |
| A Constant Contact subscription page | Robots retrieval returned HTTP 403 and the crawler skipped it. | Crawl skipped conservatively. |
| TheFreebieGuy | A normal WordPress HTML response was returned with an unverified status. | No confirmation of subscription was demonstrated by that HTML response. |

7. **Improved result interpretation and logging**

I added a submission log with the website URL, resolved submission URL, timestamp, method, submitted JSON data, HTTP status, submission status, and confirmation status. Response classification now distinguishes local acceptance, HTTP errors, some JSON application errors, CAPTCHA challenges, and successful HTTPBin echo tests. This matters because transport-level success, application acceptance, and verified registration are different outcomes.
**Issue encountered:** Each run appends new attempts to the CSV, so repeated tests increase the total count. Multiple forms on the same site may point to the same endpoint, producing duplicate attempts unless they are deduplicated. The current implementation has no complete deduplication strategy.

**Results and success estimate**

The logs changed as I reran the crawler and cleared or regenerated CSV files during development. For example, one shared snapshot had 5 attempts: 1 accepted local test, 2 CAPTCHA challenges, and 2 HTTP-success/registration-unverified responses. An earlier snapshot contained more accumulated attempts. These snapshots must not be treated as the final unique-service count.

For the submitted version, calculate final counts from the actual submission_log.csv included in the repository. Count accepted local tests and verified HTTP test echoes separately from confirmed external subscriptions. Based on the tests documented here, the crawler demonstrated successful local submission and successful external POST data transmission to HTTPBin, but no independently confirmed third-party newsletter registration. The manual Jotform submission succeeded, but it is separate from the Python crawler's automated results.

| Metric | Interpretation |
|---|---|
| Total attempts | Number of rows currently in `submission_log.csv` (may include repeat runs). |
| Accepted local submissions | Local HTTP 200 responses with the server's expected success text. |
| Verified external HTTP tests | HTTPBin responses that echoed the expected submitted data. |
| CAPTCHA challenges | Requests that returned a verification page rather than a completed registration. |
| Unverified HTTP successes | HTTP 2xx responses without proof of saved registration. |
| Confirmed external registrations | Only those separately verified through the provider or email; **none established by the supplied crawler evidence**. |

**What I would improve with more time**

1. Correct classification fallback. Return unknown for unrecognized forms rather than treating all forms as possible newsletters; require a populated email field and a manual authorization check before any external submission.
2. Restore submission safeguards. Re-enable host checks and use an explicit allowlist of test endpoints I control or am authorized to automate; prevent repeated submissions and avoid automatic redirects to other hosts.
3. Improve form extraction. Recognize nested/composite inputs, required fields, checkbox/radio selections, and labels; distinguish honeypots from normal user-facing fields without trying to defeat anti-bot protections.
4. Improve JavaScript support. Use a browser automation tool for observing JavaScript-rendered forms only on permitted sites. Respect site access restrictions and handle CAPTCHA through the normal manual user flow.
5. Improve field mapping. Use field labels, id, placeholder, and input types rather than relying on a growing list of hardcoded names.
6. Improve logging and deduplication. Store one record per reviewed form, an optional response summary, clear error categories, and separate verified registrations from requests. Avoid logging unnecessary personal or network data.
7. Improve reliability. Add timeout handling when fetching pages and robots files, fix exception logging so errors cannot reference an uninitialized response, and limit response printing to a safe summary.
8. Evaluate more systematically. Report unique eligible sites, forms detected, attempted submissions, confirmed test receipts, challenge/rejection rates, and confirmed registrations as separate denominators.