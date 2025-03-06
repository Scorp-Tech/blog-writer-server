from pollinationai import PollinationAI, PollinationAIAssistant
from bs4 import BeautifulSoup
import datetime
import json
import re
import xml.etree.ElementTree as ET
import gzip
import io
import requests
import os
from onedrive import upload_file
from urllib.parse import urlparse, ParseResult
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")


client = PollinationAI()

def fetch_sitemap(sitemap_url, visited_sitemaps=None):
    if visited_sitemaps is None:
        visited_sitemaps = set()
    
    if sitemap_url in visited_sitemaps:
        return []
    
    visited_sitemaps.add(sitemap_url)
    
    try:
        response = requests.get(sitemap_url)
        response.raise_for_status()

        # Check if the response is gzipped based on the URL extension.
        # Alternatively, you could check response.headers for 'Content-Encoding'
        if sitemap_url.endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
                xml_content = f.read()
        else:
            xml_content = response.content

        root = ET.fromstring(xml_content)
        urls = []
        
        for elem in root.iter():
            tag = elem.tag.split("}")[-1]  # Handle potential namespace prefixes
            if tag == "loc" and elem.text:
                url = elem.text.strip()
                # If the URL points to another sitemap, including gzipped ones, process it recursively.
                if url.endswith(".xml") or url.endswith(".xml.gz"):
                    urls.extend(fetch_sitemap(url, visited_sitemaps))
                else:
                    urls.append(url)
        
        return urls

    except (requests.exceptions.RequestException, ET.ParseError) as e:
        print(f"Error fetching sitemap: {e}")
        return []

class URL():
    def __init__(self, urlRes : ParseResult):
        self.fragment = urlRes.fragment
        self.hostname = urlRes.hostname
        self.netloc = urlRes.netloc
        self.params = urlRes.params
        self.password = urlRes.password
        self.path = urlRes.path
        self.port = urlRes.port
        self.query = urlRes.query
        self.scheme = urlRes.scheme
        self.username = urlRes.username
        self.paths = urlRes.path.split("/")[1:]
        self.robots = ""
        self.sitemap = ""
        
def parseUrl(website, flag = False):
    if("https" not in website): website = "https://" + website
    url = urlparse(website)
    url1 = URL(url)
    url1.robots = url.scheme + "://" + url.hostname + "/robots.txt"
    if(not flag): return url1
    response = requests.get(url1.robots)
    url1.sitemap = re.findall("(?<=Sitemap: ).*", response.text)[0]
    return url1

def groupUrls(urls):
    grouped = {}
    
    for url in urls:
        parsed = urlparse(url)
        # Split the path by '/' and filter out empty strings.
        path_parts = [part for part in parsed.path.split('/') if part]
        # If there are path parts, use the first one as the group key.
        if path_parts:
            group = path_parts[0]
        else:
            group = '/'
            
        if group in grouped:
            grouped[group].append(url)
        else:
            grouped[group] = [url]
            
    return grouped

def getGroupedUrls(website):
    parsedUrl = parseUrl(website, True)
    allUrls = fetch_sitemap(parsedUrl.sitemap)
    return groupUrls(allUrls)

def getPromotionalUrlGroups(groupedUrls:dict):
    groups = groupedUrls.keys()
    return json.loads(client.sendMessage(f"These are the groups of urls on my website, can you give me an array of groups of the urls that may be promotional like the urls in that group can be used in advertisement or blogs for commercial purpose.\nHere's the groups:\n{groups}\n\nThe output should be in form of json array and when I say json array where the key is 'promotional_groups'", response_format={"type": "json_object"}))['promotional_groups']

def getPromotionalUrls(groupedUrls: dict, promotionalGroups = None):
    if(not promotionalGroups):
        promotionalGroups = getRelevantPromotionalUrls(groupedUrls)
    res = []
    for i in groupedUrls:
        if i in promotionalGroups:
            res.extend(groupedUrls[i])
    return res

def getRelatedKeywords(keyword):
    response = requests.get(f'https://www.google.com/complete/search?q={keyword}&cp=17&client=gws-wiz&xssi=t&gs_pcrt=undefined&hl=en-IN&authuser=0&psi=KjrDZ9nRF-KRvr0P84KC2AU.1740847658821&dpr=1').text
    keywords = json.loads(client.sendMessage(f"Can you extract the keywords from this provided text and give me a json array of these keywords: {response}", model="gpt 3.5", response_format={"type": "json_object"}))['keywords']    
    res = set()
    for keyword in keywords:
        t = re.sub("[^A-z ]", "", keyword).split()
        for word in t:
            if(word.endswith('s')):
                res.add(word[:-1])
            else:
                res.add(word)
    return list(res)

def getRelevantPromotionalUrls(promotionalUrls:list, _keyword:str):
    keywords = getRelatedKeywords(_keyword)
    keywords1 = []
    for word in keywords:
        if(len(word) > 3):
            keywords1.append(word)
    visitedUrl = []
    relevanceScore = []
    for i in promotionalUrls:
        score = 0
        t = urlparse(i)
        url:str
        url = t.scheme + "://" + t.hostname + t.path
        url1 = re.sub("(\/|\.|\-|\:)", " ", url)
        url1 = re.sub("[^A-z ]", "", url1)
        if(url not in visitedUrl):
            for x, keyword in enumerate(keywords1):
                if(keyword in url):
                    score+=1
                if(keyword[:-1] in url1):
                    score += 1
            for j in range(2, 3):
                for k in range(len(keywords) - j):
                    keyword = keywords[k:k+j]
                    if(" ".join(keyword) in url1):
                        score += j
            if(score):
                relevanceScore.append({
                    "url": url,
                    "score": score
                })
            visitedUrl.append(url)
    relevanceScore = sorted(relevanceScore, key=lambda x: x['score'], reverse=True)
    return relevanceScore[:50]

def getPageContent(url, device="Mobile"):
    # Configure Chrome for headless mode.
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    if(device == "Mobile"):
        mobile_emulation = {"deviceName": "iPhone 12 Pro"}
        chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)
        time.sleep(10)
        driver.execute_script("""document.querySelectorAll('link').forEach(s=>s.remove()),document.querySelectorAll('style').forEach(s=>s.remove()),document.querySelectorAll('script').forEach(s=>s.remove()),document.querySelectorAll('*').forEach(e=>[...e.attributes].forEach(a=>{if(!["style", "height", "width", "src", "name", "alt", "title", "content", "property", "href"].includes(a.name)) e.removeAttribute(a.name)}));""")
        # Return the complete page source after JavaScript has been executed.
        page_content = driver.page_source
    finally:
        driver.quit()
        
    return page_content

def getCompanyProfile(url):
    return json.loads(client.sendMessage("Based on the following website content, extract key information about the company. "
        "Provide the details in JSON format with the following fields: \n"
        "CompanyName, Company Description, Industry, Products/Services, Mission Statement, "
        "Key Leadership, Headquarters Location, and any other relevant details. \n\n"
        "Website Content:\n" + getPageContent(url), response_format={"type": "json_object"}))

def writeCompanyData(companyName, dataName, data):
    if not os.path.exists(f'company/{companyName}'):
        os.makedirs(f'company/{companyName}')
    f = open(f"company/{companyName}/{dataName}.json", 'w')
    f.write(json.dumps(data))
    f.close()

def readCompanyData(companyName, dataName):
    f = open(f"company/{companyName}/{dataName}.json", 'r')
    data = json.loads(f.read())
    f.close()
    return data

def saveCompanyData(url):
    companyProfile = getCompanyProfile(url)
    companyName = companyProfile['CompanyName']
    writeCompanyData(companyName, "profile", companyProfile)
    allGroupedUrls = getGroupedUrls(url)
    writeCompanyData(companyName, "allGroupedUrls", allGroupedUrls)
    promotionalGroups = json.loads(client.sendMessage(f"These are the groups of urls on my website, can you give me an array of groups of the urls that may be promotional like the urls in that group can be used in advertisement or blogs for commercial purpose.\nHere's the groups:\n{allGroupedUrls.keys()}\n\nThe output should be in form of json array and when I say json array where the key is 'promotional_groups'", response_format={"type": "json_object"}))['promotional_groups']
    writeCompanyData(companyName, "promotionalGroups", promotionalGroups)

def getJavascriptRenderedPage(url):
    # Configure Chrome for headless mode.
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    #prefs = {"profile.managed_default_content_settings.images": 2}
    #chrome_options.add_experimental_option("prefs", prefs)
    mobile_emulation = {
        "deviceMetrics": {"width": 320, "height": 2000, "pixelRatio": 1.0},
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Mobile Safari/537.36"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.emulateNetworkConditions", {
            "offline": False,
            "latency": 150,  # 150 ms latency
            "downloadThroughput": (4000 * 1024) / 8,  # 4000 kbps to bytes per second
            "uploadThroughput": (3000 * 1024) / 8,      # 3000 kbps to bytes per second
        })
    try:
        driver.get(url)
        time.sleep(5)
        _screenshot = driver.get_screenshot_as_png()
        screenshot = upload_file(_screenshot, "image/crawl/screenshots", f"{re.sub('[^A-z]', '', url)}_{time.time()}.png")
        # Return the complete page source after JavaScript has been executed.
        page_content = driver.page_source
    finally:
        pass
    
    return [page_content, screenshot['url']]

def parse_html_page(html_content: str, url, screenshot) -> dict:
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract canonical URL from <link rel="canonical"> if available.
    canonical_tag = soup.find("link", rel="canonical")
    if canonical_tag and canonical_tag.get("href"):
        url = canonical_tag.get("href")
    
    # Derive scheme from URL
    scheme = url.split("://")[0] if "://" in url else "http"
    
    # Get page title
    title_tag = soup.title
    title = title_tag.get_text(strip=True) if title_tag else "Anniversary Gifts Collection"
    
    # Get meta description
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_desc_tag.get("content", "").strip() if meta_desc_tag else "Discover our curated collection of anniversary gifts."
    
    # Get meta keywords and split them into a list
    meta_keywords_tag = soup.find("meta", attrs={"name": "keywords"})
    if meta_keywords_tag and meta_keywords_tag.get("content"):
        meta_keywords = [kw.strip() for kw in meta_keywords_tag.get("content", "").split(",") if kw.strip()]
    else:
        meta_keywords = ["anniversary", "gifts", "celebration"]
    
    # Extract all links with href attributes
    links = []
    for a in soup.find_all("a", href=True):
        link_text = a.get_text(strip=True)
        link_href = a.get("href")
        links.append({
            "href": link_href,
            "text": link_text
        })
    
    videos = len(soup.find_all("video"))
    images = len(soup.find_all("image"))
    
    # Create the final dictionary using current UTC time for "crawledAt"
    parsed_data = {
        "url": url,
        "scheme": scheme,
        "status": "success",
        "crawledAt": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "crawlDetails": {
            "crawledAs": "Rank UP Scrawl Bot",
            "crawlAllowed": True,
            "pageFetch": "Successful",
            "indexingAllowed": True,
            "indexing": {
                "userDeclaredCanonical": url,
            },
            "inspectedURL": url
        },
        "data": {
            "title": title,
            "pageContent": html_content,
            "screenshot": screenshot,
            "meta": {
                "description": meta_description,
                "keywords": meta_keywords
            },
            "numberOfVideos": videos,
            "numberOfImages": images,
            "headers": {
                "Content-Type": "text/html; charset=UTF-8",
                "Date": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            },
            "links": links
        }
    }
    
    return parsed_data
