import time
import requests
from datetime import datetime
import json
import os
import re
from api import push_vouchers
from api import push_latest_date

def fetch_relevant_voucher_jsons(base_url):
    """
    Fetches relevant voucher JSON data from the specified base URL.
    
    Parameters:
    - base_url (str): The URL from which to fetch the voucher data.
    
    Returns:
    - list: A list of JSON strings containing relevant voucher information.
    """
    voucher_jsons = []
    page_content = requests.get(base_url).content.decode("utf-8")
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


def get_all_urls(base_url):
    """
    Extracts voucher URLs from the specified base URL's HTML content.
    
    Parameters:
    - base_url (str): The base URL to scrape for voucher URLs.
    
    Returns:
    - list: A list of complete voucher URLs.
    """
    html_content = requests.get(base_url).content.decode("utf-8")
    pattern = ',"url":"/[^{]*?-gutschein.'
    matches = re.findall(pattern, html_content)

    urls = [
        "https://gutscheine.blick.ch/" + match.group(1) + "-gutschein" + ('e' if match.group(0)[-1] == 'e' else '')
        for match in (re.search(r'/([^/]*)-gutschein.', m) for m in matches) if match
    ]

    return urls

def main_execution(max_voucher_age, verbose=False): 
    blick_overview_url = "https://gutscheine.blick.ch/alle-shops"
    urls = get_all_urls(blick_overview_url)
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
        

        try:
            voucher_jsons = fetch_relevant_voucher_jsons(url)

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


if __name__ == "__main__":
    INFINITE_EXECUTION = True  
    VOUCHER_REFRESH_RATE = 86400/2  # Time between searching the same website for vouchers 
    SEARCH_RATE = 3600  # Time between checking the ages of the vouchers. Especially relevant if a website or the internet is not reliable

    # First iteration always searches new vouchers 
    last_check_time = time.time() 
    main_execution(max_voucher_age=0, verbose=True)
    
    while INFINITE_EXECUTION: 
        time.sleep(max(SEARCH_RATE - (time.time()-last_check_time), 60))
        last_check_time = time.time() 
       
        try: 
            main_execution(VOUCHER_REFRESH_RATE, verbose=False)
            print(f"Updated vouchers at {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        except Exception as e: 
            print(f"Failed to update vouchers at {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n{e}")
 


