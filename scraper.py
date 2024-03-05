import random
import time
import requests
import datetime
import json
import os
import re
from api import push_vouchers
from api import push_latest_date

def fetch_relevant_voucher_jsons(base_url, session):
    """
    Fetches relevant voucher JSON data from the specified base URL.
    
    Parameters:
    - base_url (str): The URL from which to fetch the voucher data.
    
    Returns:
    - list: A list of JSON strings containing relevant voucher information.
    """
    voucher_jsons = []
    page_content = session.get(base_url).content.decode("utf-8")
    remaining_content = page_content.split('"expired_codes":')[-1]

    if ',"expired_deals":' in remaining_content:
        first_json, remaining_content = remaining_content.split(',"expired_deals":', 1)
        voucher_jsons.append(remove_json_tail(first_json))

    if ']},{"widget_api_mapping"' in remaining_content:
        second_json, remaining_content = remaining_content.split(']},{"widget_api_mapping"', 1)
        voucher_jsons.append(second_json + "]")

    if ',"vouchers":' in remaining_content:
        _, vouchers_content = remaining_content.split(',"vouchers":', 1)
        third_json, remaining_content = vouchers_content.split(',"expiredVouchers":', 1)
        voucher_jsons.append(remove_json_tail(third_json))

    fourth_json = remaining_content.split('"similarVouchers":')[0]
    voucher_jsons.append(remove_json_tail(fourth_json))

    return voucher_jsons


def remove_json_tail(json_string):
    """
    Trims a JSON string to remove any trailing content after the last closing bracket.
    
    Parameters:
    - json_string (str): The JSON string to be trimmed.
    
    Returns:
    - str: The trimmed JSON string.
    """
    last_bracket_index = json_string.rfind(']')
    return json_string[:last_bracket_index + 1] if last_bracket_index != -1 else json_string


def parse_vouchers(voucher_string):
    """
    Parses a string of JSON formatted voucher data.
    
    Parameters:
    - voucher_string (str): The JSON string containing voucher data.
    
    Returns:
    - list: A list of dictionaries with voucher information.
    """
    vouchers = json.loads(voucher_string)
    return [{
        'code': voucher.get('code'),
        'description': voucher.get('title'),
        'creation_date': voucher.get('creation_time'),
        'expiration_date': voucher.get('end_time'),
    } for voucher in vouchers]


def save_vouchers_to_json(vouchers, url, file_name, directory="Voucher_JSONs", verbose=False):
    """
    Saves voucher data and the source URL to a specified JSON file.
    
    Parameters:
    - vouchers (list): The list of voucher dictionaries to save.
    - url (str): The source URL to include in the saved JSON.
    - file_name (str): The name of the file to save the data to.
    - directory (str): The directory to save the file in. Defaults to "Voucher_JSONs".
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_path = os.path.join(directory, file_name)
    data = {"URL": url, "vouchers": vouchers}

    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    if verbose:
        print(f"Saved {len(vouchers)} vouchers to {file_path}")


def get_all_urls(base_url, session):
    """
    Extracts voucher URLs from the specified base URL's HTML content.
    
    Parameters:
    - base_url (str): The base URL to scrape for voucher URLs.
    
    Returns:
    - list: A list of complete voucher URLs.
    """
    html_content = session.get(base_url).content.decode("utf-8")
    pattern = ',"url":"/[^{]*?-gutschein.'
    matches = re.findall(pattern, html_content)

    urls = [
        "https://gutscheine.blick.ch/" + match.group(1) + "-gutschein" + ('e' if match.group(0)[-1] == 'e' else '')
        for match in (re.search(r'/([^/]*)-gutschein.', m) for m in matches) if match
    ]

    return urls

def voucher_collection(max_voucher_age, session, verbose=False): 
    blick_overview_url = "https://gutscheine.blick.ch/alle-shops"
    urls = get_all_urls(blick_overview_url, session)
    if verbose: 
        print(f"Found {len(urls)} websites with vouchers on {blick_overview_url}")

    for i, url in enumerate(urls):


        filename = "blick_" + url.split("/")[-1] + ".json"

        file_path = os.path.join("Voucher_JSONs", filename)

        
        if os.path.exists(file_path):
            file_age = time.time() - os.path.getmtime(file_path)
            if file_age < max_voucher_age:
                if verbose:
                    print(f"Skipping {filename}, recently updated.")
                continue
        
        if i>0: 
            powernap()

        try:
            voucher_jsons = fetch_relevant_voucher_jsons(url, session)

            all_vouchers = [voucher for json_str in voucher_jsons for voucher in parse_vouchers(json_str)]

            # push to firebase
            name = url.split("/")[-1]
            stripped_vouchers = [  # all_vouchers but without the creation_date and expiration_date
                {key: value for key, value in voucher.items() if key not in ["creation_date", "expiration_date"]} for
                voucher in all_vouchers]

            # ----------

            save_vouchers_to_json(all_vouchers, url, filename, verbose=verbose)
            push_vouchers(name, stripped_vouchers, verbose=verbose)
        except Exception as e:
            print(f"Error processing {url}: {e}")
    push_latest_date(verbose=verbose)


def powernap(mean = 10, stddev = 5): 
    time.sleep(max(3,(random.gauss(mean, stddev))))


if __name__ == "__main__":
    INFINITE_EXECUTION = True  
    VOUCHER_REFRESH_RATE = 86400/2  # Any voucher older than this will be replaced the next time vouchers are searched
    SEARCH_TIME = 19  # Which hour of the day the search will occur on on average
    SEARCH_TIME_DEVIATION = 600  # Standard deviation of starting time of the search
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

    with requests.Session() as session:
        session.headers.update(HEADERS)
        # First iteration always searches new vouchers 
        voucher_collection(max_voucher_age=0, session=session, verbose=True)
    

    while INFINITE_EXECUTION: 

        # Calculate the time we sleep for
        now = datetime.datetime.now()
        next_target = now.replace(hour=SEARCH_TIME, minute=0, second=0, microsecond=0)
        if now >= next_target:
            # If it's past the target hour already, calculate the next occurrence for the following day
            next_target += datetime.timedelta(days=1)
        sleep_time = (next_target - now).total_seconds() + random.gauss(0, SEARCH_TIME_DEVIATION)
        
        print(f"Next time vouchers will be checked: {now + datetime.timedelta(seconds=sleep_time)}")
        time.sleep(sleep_time)
       
        try: 
            with requests.Session() as session:
                session.headers.update(HEADERS)
                # First iteration always searches new vouchers
                voucher_collection(VOUCHER_REFRESH_RATE, session=session, verbose=False)
            print(f"Updated vouchers at {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        except Exception as e: 
            print(f"Failed to update vouchers at {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n{e}")
 


