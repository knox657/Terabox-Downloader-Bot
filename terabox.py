import re
from urllib.parse import parse_qs, urlparse
import requests
from config import COOKIE
from tools import get_formatted_sizeimport re
from urllib.parse import parse_qs, urlparse

import requests

from config import COOKIE
from tools import get_formatted_size


def check_url_patterns(url):
    patterns = [
        r"ww\.mirrobox\.com",
        r"www\.nephobox\.com",
        r"freeterabox\.com",
        r"www\.freeterabox\.com",
        r"1024tera\.com",
        r"4funbox\.co",
        r"www\.4funbox\.com",
        r"mirrobox\.com",
        r"nephobox\.com",
        r"terabox\.app",
        r"terabox\.com",
        r"www\.terabox\.ap",
        r"www\.terabox\.com",
        r"www\.1024tera\.co",
        r"www\.momerybox\.com",
        r"teraboxapp\.com",
        r"momerybox\.com",
        r"tibibox\.com",
        r"www\.tibibox\.com",
        r"www\.teraboxapp\.com",
    ]

    for pattern in patterns:
        if re.search(pattern, url):
            return True

    return False


def get_urls_from_string(string: str) -> list[str]:
    """
    Extracts URLs from a given string.

    Args:
        string (str): The input string from which to extract URLs.

    Returns:
        list[str]: A list of URLs extracted from the input string. If no URLs are found, an empty list is returned.
    """
    pattern = r"(https?://\S+)"
    urls = re.findall(pattern, string)
    urls = [url for url in urls if check_url_patterns(url)]
    if not urls:
        return []
    return urls[0]


def find_between(data: str, first: str, last: str) -> str | None:
    """
    Searches for the first occurrence of the `first` string in `data`,
    and returns the text between the two strings.

    Args:
        data (str): The input string.
        first (str): The first string to search for.
        last (str): The last string to search for.

    Returns:
        str | None: The text between the two strings, or None if the
            `first` string was not found in `data`.
    """
    try:
        start = data.index(first) + len(first)
        end = data.index(last, start)
        return data[start:end]
    except ValueError:
        return None


def extract_surl_from_url(url: str) -> str | None:
    """
    Extracts the surl parameter from a given URL.

    Args:
        url (str): The URL from which to extract the surl parameter.

    Returns:
        str: The surl parameter, or False if the parameter could not be found.
    """
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    surl = query_params.get("surl", [])

    if surl:
        return surl[0]
    else:
        return False


def get_data(url: str):
    r = requests.Session()
    headersList = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Connection": "keep-alive",
        # "Cookie": COOKIE,
        "Cookie": "csrfToken=lkl0St5ZVVpUOmG-WmRfO-69; browserid=MxLQF6jBJw1xP28gi4iKO-enTAN0xjWwKiGnt8iIEzi0trArdkS8w9aTGOI=; lang=en; TSID=lLS9D5L3HRJi9TMK7ay74tzWX2NTlQD0; __bid_n=18eebeacd60c6d12b14207; ab_ymg_result={"data":"8b0482c84aac99214162666d7e1afaa067b555fca2e1a140699274e5d06f440bc0de3c0ac164722246f8021b23ba07cb7bb59fa4848e942bb6d53e0b3559adc291bffe238151db00da88969983dc031a8d6ab547d36212d32be7b490a643cf789cf3262d42b4e7200bec8805ac861f520a7a9131b02f66af80fa51028d7cd41b","key_id":"66","sign":"fde50190"}; _ga=GA1.1.1109738107.1713355841; ndut_fmt=73B61A1F24E9AF9C6F2177F702D8D5FDA9AF486347B2F8A6DAB9DB961D312016; ab_sr=1.0.1_NTRiMWMwNjg0YjRlMDZiZmVhNGYxODI4NGJkNTYwMDM2YzcwZTg2YmU4NjExZmU3MzNjYzVmZDYyYzUwYWQ1MDVjNDU4ZDUyY2ZmYWFlZDcwOWY3YmIwNzY5ZmY4MTUwMDFkYTFlYmEzNGJmYTA1MzU1YzhmNDI3NmQ1ZjExMGRiMGVjN2Q1YjkwNTVlNzkwNGM2YzVlYmJiNDk4NWMyMg==; _ga_06ZNKL8C2E=GS1.1.1713360517.3.0.1713360533.44.",
        "DNT": "1",
        "Host": "www.terabox.app",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    payload = ""

    response = r.get(url, data=payload, headers=headersList)
    response = r.get(response.url, data=payload, headers=headersList)
    logid = find_between(response.text, "dp-logid=", "&")
    jsToken = find_between(response.text, "fn%28%22", "%22%29")
    bdstoken = find_between(response.text, 'bdstoken":"', '"')
    shorturl = extract_surl_from_url(response.url)
    if not shorturl:
        return False

    reqUrl = f"https://www.terabox.app/share/list?app_id=250528&web=1&channel=0&jsToken={jsToken}&dp-logid={logid}&page=1&num=20&by=name&order=asc&site_referer=&shorturl={shorturl}&root=1"

    headersList = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Connection": "keep-alive",
        # "Cookie":Cookie,
        "Cookie": "csrfToken=lkl0St5ZVVpUOmG-WmRfO-69; browserid=MxLQF6jBJw1xP28gi4iKO-enTAN0xjWwKiGnt8iIEzi0trArdkS8w9aTGOI=; lang=en; TSID=lLS9D5L3HRJi9TMK7ay74tzWX2NTlQD0; __bid_n=18eebeacd60c6d12b14207; ab_ymg_result={"data":"8b0482c84aac99214162666d7e1afaa067b555fca2e1a140699274e5d06f440bc0de3c0ac164722246f8021b23ba07cb7bb59fa4848e942bb6d53e0b3559adc291bffe238151db00da88969983dc031a8d6ab547d36212d32be7b490a643cf789cf3262d42b4e7200bec8805ac861f520a7a9131b02f66af80fa51028d7cd41b","key_id":"66","sign":"fde50190"}; _ga=GA1.1.1109738107.1713355841; ndut_fmt=73B61A1F24E9AF9C6F2177F702D8D5FDA9AF486347B2F8A6DAB9DB961D312016; ab_sr=1.0.1_NTRiMWMwNjg0YjRlMDZiZmVhNGYxODI4NGJkNTYwMDM2YzcwZTg2YmU4NjExZmU3MzNjYzVmZDYyYzUwYWQ1MDVjNDU4ZDUyY2ZmYWFlZDcwOWY3YmIwNzY5ZmY4MTUwMDFkYTFlYmEzNGJmYTA1MzU1YzhmNDI3NmQ1ZjExMGRiMGVjN2Q1YjkwNTVlNzkwNGM2YzVlYmJiNDk4NWMyMg==; _ga_06ZNKL8C2E=GS1.1.1713360517.3.0.1713360533.44.",
        "DNT": "1",
        "Host": "www.terabox.app",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    payload = ""

    response = r.get(reqUrl, data=payload, headers=headersList)

    if not response.status_code == 200:
        return False
    r_j = response.json()
    if r_j["errno"]:
        return False
    if not "list" in r_j and not r_j["list"]:
        return False

    response = r.head(r_j["list"][0]["dlink"], headers=headersList)
    direct_link = response.headers.get("location")
    data = {
        "file_name": r_j["list"][0]["server_filename"],
        "link": r_j["list"][0]["dlink"],
        "direct_link": direct_link,
        "thumb": r_j["list"][0]["thumbs"]["url3"],
        "size": get_formatted_size(int(r_j["list"][0]["size"])),
        "sizebytes": int(r_j["list"][0]["size"]),
    }
    return data

def check_url_patterns(url):
    patterns = [
        r"ww\.mirrobox\.com",
        r"www\.nephobox\.com",
        r"freeterabox\.com",
        r"www\.freeterabox\.com",
        r"1024tera\.com",
        r"4funbox\.co",
        r"www\.4funbox\.com",
        r"mirrobox\.com",
        r"nephobox\.com",
        r"terabox\.app",
        r"terabox\.com",
        r"www\.terabox\.ap",
        r"www\.terabox\.com",
        r"www\.1024tera\.co",
        r"www\.momerybox\.com",
        r"teraboxapp\.com",
        r"momerybox\.com",
        r"tibibox\.com",
        r"www\.tibibox\.com",
        r"www\.teraboxapp\.com",
    ]

    for pattern in patterns:
        if re.search(pattern, url):
            return True

    return False


def get_urls_from_string(string: str) -> list[str]:
    pattern = r"(https?://\S+)"
    urls = re.findall(pattern, string)
    urls = [url for url in urls if check_url_patterns(url)]
    if not urls:
        return []
    return urls[0]


def find_between(data: str, first: str, last: str) -> str | None:
    try:
        start = data.index(first) + len(first)
        end = data.index(last, start)
        return data[start:end]
    except ValueError:
        return None


def extract_surl_from_url(url: str) -> str | None:
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    surl = query_params.get("surl", [])
    if surl:
        return surl[0]
    else:
        return False


def get_data(url: str):
    r = requests.Session()
    headersList = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Connection": "keep-alive",
        "Cookie": COOKIE,
        "DNT": "1",
        "Host": "www.terabox.app",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    payload = ""

    response = r.get(url, data=payload, headers=headersList)
    response = r.get(response.url, data=payload, headers=headersList)
    logid = find_between(response.text, "dp-logid=", "&")
    jsToken = find_between(response.text, "fn%28%22", "%22%29")
    bdstoken = find_between(response.text, 'bdstoken":"', '"')
    shorturl = extract_surl_from_url(response.url)
    if not shorturl:
        return False

    reqUrl = f"https://www.terabox.app/share/list?app_id=250528&web=1&channel=0&jsToken={jsToken}&dp-logid={logid}&page=1&num=20&by=name&order=asc&site_referer=&shorturl={shorturl}&root=1"

    headersList = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Connection": "keep-alive",
        "Cookie": COOKIE,
        "DNT": "1",
        "Host": "www.terabox.app",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    payload = ""

    response = r.get(reqUrl, data=payload, headers=headersList)

    if not response.status_code == 200:
        return False
    r_j = response.json()
    if r_j.get("errno"):
        return False
    if "list" not in r_j or not r_j["list"]:
        return False
    direct_link = r_j["list"][0].get("dlink")
    if not direct_link:
        return False
    response = r.head(direct_link, headers=headersList)
    direct_link = response.headers.get("location")
    data = {
        "file_name": r_j["list"][0]["server_filename"],
        "link": r_j["list"][0]["dlink"],
        "direct_link": direct_link,
        "thumb": r_j["list"][0]["thumbs"]["url3"],
        "size": get_formatted_size(int(r_j["list"][0]["size"])),
        "sizebytes": int(r_j["list"][0]["size"]),
    }
    return data

