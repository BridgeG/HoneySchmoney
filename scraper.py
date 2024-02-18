import time
import requests
import json
import os 
import re

def fetch_relevant_voucher_jsons(base_url):
    """
    Fetches relevant voucher JSON data from the specified base URL.
    
    Parameters:
    - base_url: The URL from which to fetch the voucher data.
    
    Returns:
    - A list of JSON strings containing relevant voucher information.
    """
    voucher_jsons = []
    # Fetch the page content and split to get the relevant part
    remaining_page_content = requests.get(base_url).content.decode("utf-8").split('"expired_codes":')[-1]
    
    # Extract the first JSON and the rest of the content
    if ',"expired_deals":' in remaining_page_content: 
        first_json, remaining_page_content = remaining_page_content.split(',"expired_deals":')
        voucher_jsons.append(remove_json_tail(first_json))
    

    # Extract the second JSON and the rest of the content
    if ']},{"widget_api_mapping"' in remaining_page_content: 
        second_json = remaining_page_content.split(']},{"widget_api_mapping"')[0]
        voucher_jsons.append(second_json + "]")
        remaining_page_content = remaining_page_content.split(']},{"widget_api_mapping"')[-1]
    
    # Ignore irrelevant part and extract the third JSON
    if ',"vouchers":' in remaining_page_content: 
        _, remaining_page_content = remaining_page_content.split(',"vouchers":')
        third_json, remaining_page_content = remaining_page_content.split(',"expiredVouchers":')
        voucher_jsons.append(remove_json_tail(third_json))

    # Extract the fourth JSON
    fourth_json = remaining_page_content.split('"similarVouchers":')[0]
    voucher_jsons.append(remove_json_tail(fourth_json))

    return voucher_jsons

def remove_json_tail(json_string):
    """
    Removes all characters after the last ']' in the JSON string.
    
    Parameters:
    - json_string: The JSON string to process.
    
    Returns:
    - The processed JSON string with characters after the last ']' removed.
    """
    last_bracket_index = json_string.rfind(']')
    # If ']' is found, slice up to and including this index
    if last_bracket_index != -1:
        return json_string[:last_bracket_index + 1]
    return json_string

def parse_vouchers(voucher_string):
    """
    Parses the voucher information from a JSON string.
    
    Parameters:
    - voucher_string: The JSON string containing voucher data.
    
    Returns:
    - A list of dictionaries with parsed voucher information.
    """
    vouchers = json.loads(voucher_string)
    parsed_vouchers = []

    for voucher in vouchers:
        # Extract necessary information
        voucher_code = voucher.get('code', None)
        description = voucher.get('title', None)
        creation_time = voucher.get('creation_time', None)
        end_time = voucher.get('end_time', None)

        parsed_vouchers.append({
            'code': voucher_code,
            'description': description,
            'creation_date': creation_time,
            'expiration_date': end_time,
        })

    return parsed_vouchers

def save_vouchers_to_json(vouchers, url, file_name, directory = "Voucher_JSONs"):
    """
    Saves the vouchers and the URL to a JSON file within the 'Voucher_JSONs' directory.
    
    Parameters:
    - vouchers: A list of dictionaries containing voucher information.
    - url: The URL to include in the JSON.
    - file_name: The name of the file to save the JSON to.
    - directory: The path of the fodler to save the JSON to (default set to "Voucher_JSONs")
    """
    
    # Create the directory if it does not exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Path for the file to save
    file_path = os.path.join(directory, file_name)
    
    # Create a dictionary to hold the vouchers and the URL
    data_to_save = {
        "URL": url,
        "vouchers": vouchers
    }
    
    # Convert the dictionary to a JSON string
    json_string = json.dumps(data_to_save, indent=4)
    
    # Save the JSON string to a file
    with open(file_path, 'w') as json_file:
        json_file.write(json_string)

    print(f"Saved {len(vouchers)} vouchers to {file_path}")

def get_all_urls(base_url):
    html = requests.get(base_url).content.decode("utf-8")
    pattern = ',"url":"/[^{]*?-gutschein.'

     # Find all substrings that match the pattern
    matches = re.findall(pattern, html)
    
    # Process matches to include 'e' at the end if present, exclude the dot otherwise
    processed_matches = []
    for match in matches:
        # Extract the /XXX-gutschein part
        part = re.search(r'/([^/]*)-gutschein.', match)
        if part:
            extracted = part.group(1) + "-gutschein"
            # Check if the last character in the original match is 'e', include it if so
            if match[-1] == 'e':
                processed_matches.append(extracted + 'e')
            else:
                processed_matches.append(extracted)

    for i in range(len(processed_matches)): 
        processed_matches[i] = "https://gutscheine.blick.ch/" + processed_matches[i]

    return processed_matches

if __name__ == "__main__":
    blick_overview_url = "https://gutscheine.blick.ch/alle-shops"
    directory = "Voucher_JSONs"
    max_age = 3600

    urls = get_all_urls(blick_overview_url)
    print(f"Found {len(urls)} websites with vouchers on {blick_overview_url}")

    for i, url in enumerate(urls):

        filename = url.split("/")[-1]
        if "gutscheine.blick.ch" in url: 
            filename = f"blick_{filename}.json"


        if os.path.exists(os.path.join(directory, filename)):
            file_age = time.time() - os.path.getmtime(os.path.join(directory, filename))
            if file_age < max_age:
                print(f"Found {os.path.join(directory, filename)} with age of just {round(file_age)} seconds. The vouchers will only be renewed after {max_age} seconds")
                print(f"{i+1}/{len(urls)} voucher-pages processed")
                continue
        try: 
            voucher_jsons = fetch_relevant_voucher_jsons(url)
            all_vouchers = []

            for voucher_json in voucher_jsons:
                all_vouchers.extend(parse_vouchers(voucher_json))

            save_vouchers_to_json(all_vouchers, url, filename, directory)
        except Exception as e: 
            print(f"------------------Exception in {url}------------------\n{e}\n")
        print(f"{i+1}/{len(urls)} voucher-pages processed")

