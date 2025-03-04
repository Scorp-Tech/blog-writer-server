from bs4 import BeautifulSoup

from bs4 import BeautifulSoup
import datetime


# Example usage:
if __name__ == "__main__":
    sample_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <title>Anniversary Gifts Collection</title>
      <meta name="description" content="Discover our curated collection of anniversary gifts.">
      <meta name="keywords" content="anniversary, gifts, celebration">
      <link rel="canonical" href="https://www.pinenlime.com/collections/anniversary-gifts">
    </head>
    <body>
      <a href="https://www.example.com/more-info">More Info</a>
    </body>
    </html>
    """
    result = parse_html_page(sample_html)
    import json
    print(json.dumps(result, indent=2))
