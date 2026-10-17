
from bs4 import BeautifulSoup

html = """
<form action="/subscribe" method="get">
    <input name="name" type="text">
    <input name="email" type="email">
    <button type="submit">Subscribe</button>
</form>
"""

soup = BeautifulSoup(html, "html.parser")

for form in soup.find_all("form"):
    print("Action:", form.get("action"))
    print("Method:", form.get("method", "No method specified"))

    for field in form.find_all("input"):
        print("Field:", field.get("name", "No name specified"), 
              "Type:", field.get("type", "No type specified"))

    for button in form.find_all("button"):
        print("Button:", button.get_text(strip=True),
              "Type:", button.get("type", "No type specified"))
        
