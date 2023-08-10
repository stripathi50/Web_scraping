import warnings
import pandas as pd
import os
import re
from datetime import datetime
import time
from bs4 import BeautifulSoup
import requests

''' Request Functions starts '''


def status_log(r):
    """Pass response as a parameter to this function"""
    url_log_file = 'url_log.txt'
    if not os.path.exists(os.getcwd() + '\\' + url_log_file):
        with open(url_log_file, 'w') as f:
            f.write('url, status_code\n')
    with open(url_log_file, 'a') as file:
        file.write(f'{r.url}, {r.status_code}\n')


def sup_sub_encode(html):
    """Encodes superscript and subscript tags"""
    encoded_html = html.replace('<sup>', 's#p').replace('</sup>', 'p#s').replace('<sub>', 's#b').replace('</sub>',
                                                                                                         'b#s') \
        .replace('<Sup>', 's#p').replace('</Sup>', 'p#s').replace('<Sub>', 's#b').replace('</Sub>', 'b#s')
    encoded_html = BeautifulSoup(encoded_html, 'html.parser').text.strip()
    return encoded_html


def sup_sub_decode(html):
    """Decodes superscript and subscript tags"""
    decoded_html = html.replace('s#p', '<sup>').replace('p#s', '</sup>').replace('s#b', '<sub>').replace('b#s',
                                                                                                         '</sub>')
    # decoded_html = BeautifulSoup(decoded_html, 'html.parser')
    return decoded_html


def retry(func, retries=3):
    """Decorator function"""
    retry.count = 0

    def retry_wrapper(*args, **kwargs):
        attempt = 0
        while attempt < retries:
            try:
                return func(*args, **kwargs)
            except requests.exceptions.ConnectionError as e:
                attempt += 1
                total_time = attempt * 10
                print(f'Retrying {attempt}: Sleeping for {total_time} seconds, error: ', e)
                time.sleep(total_time)
            if attempt == retries:
                retry.count += 1
                url_log_file = 'url_log.txt'
                if not os.path.exists(os.getcwd() + '\\' + url_log_file):
                    with open(url_log_file, 'w') as f:
                        f.write('url, status_code\n')
                with open(url_log_file, 'a') as file:
                    file.write(f'{args[0]}, requests.exceptions.ConnectionError\n')
            if retry.count == 3:
                print("Stopped after retries, check network connection")
                raise SystemExit

    return retry_wrapper


def abstract_cleaner(abstract):
    """Converts all the sup and sub script when passing the abstract block as html"""
    conversion_tags_sub = BeautifulSoup(str(abstract), 'lxml').find_all('sub')
    conversion_tags_sup = BeautifulSoup(str(abstract), 'lxml').find_all('sup')
    abstract_text = str(abstract).replace('<.', '< @@dot@@')
    for tag in conversion_tags_sub:
        original_tag = str(tag)
        key_list = [key for key in tag.attrs.keys()]
        for key in key_list:
            del tag[key]
        abstract_text = abstract_text.replace(original_tag, str(tag))
    for tag in conversion_tags_sup:
        original_tag = str(tag)
        key_list = [key for key in tag.attrs.keys()]
        for key in key_list:
            del tag[key]
        abstract_text = abstract_text.replace(original_tag, str(tag))
    abstract_text = sup_sub_encode(abstract_text)
    abstract_text = BeautifulSoup(abstract_text, 'lxml').text
    abstract_text = sup_sub_decode(abstract_text)
    abstract_text = re.sub('\s+', ' ', abstract_text)
    text = re.sub('([A-Za-z])(\s+)?(:|\,|\.)', r'\1\3', abstract_text)
    text = re.sub('(:|\,|\.)([A-Za-z])', r'\1 \2', text)
    text = re.sub('(<su(p|b)>)(\s+)(\w+)(</su(p|b)>)', r'\3\1\4\5', text)
    text = re.sub('(<su(p|b)>)(\w+)(\s+)(</su(p|b)>)', r'\1\3\5\4', text)
    text = re.sub('(<su(p|b)>)(\s+)(\w+)(\s+)(</su(p|b)>)', r'\3\1\4\6\5', text)
    abstract_text = re.sub('\s+', ' ', text)
    abstract_text = abstract_text.replace('< @@dot@@', '<.')
    return abstract_text.strip()


@retry
def post_json_response(url, headers=None, payload=None):
    """Returns the json response of the page when given with the url and headers"""
    ses = requests.session()
    r = ses.post(url, headers=headers, json=payload)
    if r.status_code == 200:
        return r.json()
    elif 499 >= r.status_code >= 400:
        print(f'client error response, status code {r.status_code} \nrefer: {r.url}')
        status_log(r)
    elif 599 >= r.status_code >= 500:
        print(f'server error response, status code {r.status_code} \nrefer: {r.url}')
        count = 1
        while count != 10:
            print('while', count)
            r = ses.post(url, headers=headers, data=payload)  # your request get or post
            print('status_code: ', r.status_code)
            if r.status_code == 200:
                # data_ = decode_base64(r.text)
                return r.json()
                # print('done', count)
            else:
                print('retry ', count)
                count += 1
                # print(count * 2)
                time.sleep(count * 2)
    else:
        status_log(r)
        return None


@retry
def get_json_response(url, headers=None):
    """Returns the json response of the page when given with the of an url and headers"""
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data_ = r.json()
        return data_
    elif 499 >= r.status_code >= 400:
        print(f'client error response, status code {r.status_code} \nrefer: {r.url}')
        status_log(r)
    elif 599 >= r.status_code >= 500:
        print(f'server error response, status code {r.status_code} \nrefer: {r.url}')
        count = 1
        while count != 10:
            print('while', count)
            r = requests.get(url, headers=headers)  # your request get or post
            print('status_code: ', r.status_code)
            if r.status_code == 200:
                data_ = r.json()
                return data_
                # print('done', count)
            else:
                print('retry ', count)
                count += 1
                # print(count * 2)
                time.sleep(count * 2)
    else:
        status_log(r)
        return None


@retry
def post_soup(url, headers=None, payload=None):
    '''returns the soup of the page when given with the of an url and headers'''
    refer = r'https://developer.mozilla.org/en-US/docs/Web/HTTP/Status#server_error_responses'
    r = requests.Session().post(url, headers=headers, json=payload, timeout=30)
    r.encoding = r
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, features="xml")
        return soup
    elif 499 >= r.status_code >= 400:
        print(f'client error response, status code {r.status_code} \nrefer: {r.url}')
        status_log(r)
    elif 599 >= r.status_code >= 500:
        print(f'server error response, status code {r.status_code} \nrefer: {r.url}')
        count = 1
        while count != 10:
            print('while', count)
            r = requests.Session().post(url, headers=headers, data=payload)  # your request get or post
            r.encoding = r
            print('status_code: ', r.status_code)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                return soup
                # print('done', count)
            else:
                print('retry ', count)
                count += 1
                # print(count * 2)
                time.sleep(count * 2)
    else:
        status_log(r)
        return None


@retry
def get_soup(url, headers=None):
    '''returns the soup of the page when given with the of an url and headers'''
    refer = r'https://developer.mozilla.org/en-US/docs/Web/HTTP/Status#server_error_responses'
    r = requests.Session().get(url, headers=headers)
    r.encoding = r
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        return soup
    elif 499 >= r.status_code >= 400:
        print(f'client error response, status code {r.status_code} \nrefer: {r.url}')
        status_log(r)
    elif 599 >= r.status_code >= 500:
        print(f'server error response, status code {r.status_code} \nrefer: {r.url}')
        count = 1
        while count != 10:
            print('while', count)
            r = requests.Session().get(url, headers=headers)  # your request get or post
            r.encoding = r
            print('status_code: ', r.status_code)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                return soup
                # print('done', count)
            else:
                print('retry ', count)
                count += 1
                # print(count * 2)
                time.sleep(count * 2)
    else:
        status_log(r)
        return None


def strip_it(text):
    return re.sub(r"\s+", ' ', text).strip()


def write_visited_log(url):
    with open(f'Visited_urls.txt', 'a', encoding='utf-8') as file:
        file.write(f'{url}\n')


def read_log_file():
    if os.path.exists('Visited_urls.txt'):
        with open('Visited_urls.txt', 'r', encoding='utf-8') as read_file:
            return read_file.read().split('\n')
    return []

def get_next_page(base_url, page_num, headers=None):
    url = f"{base_url}/{page_num}"
    return get_soup(url, headers)


# Function to remove square brackets from the text
def remove_square_brackets(text):
    # Find the index of the first '[' and the index of the last ']'
    start_index = text.find('[')
    end_index = text.rfind(']')

    # Return the text without the square brackets
    return text[start_index + 1:end_index]

if __name__ == '__main__':
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://afjare.org/',
        'Sec-Ch-Ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    JOURNAL_NAME = os.path.basename(__file__).rstrip('.py')
    BASE_URL = 'https://afjare.org/'
    src_url = BASE_URL
    print('processing journal url----> ', src_url)
    journal_soup = get_soup(src_url, headers)
    journal_name = 'African Journal of Agricultural and Resource Economics'
    journal_url = src_url
    ISSN='ISSN 2521-9871;ISSN 1993-3738'

    # Find the parent element containing the volume links
    volume_menu = journal_soup.find('ul', class_='hfe-nav-menu')

    # Find all the submenu items under the "Publications" section
    submenu_items = volume_menu.find_all('li', class_='menu-item-type-taxonomy')

    # Find all the individual volume items
    volume_items = volume_menu.find_all('li', class_='menu-item-type-post_type')

    # Create lists to store volume names and URLs
    volume_names = []
    volume_urls = []

    # Loop through the submenu items to extract volume names and URLs
    for submenu_item in submenu_items:
        volume_name = submenu_item.a.text.strip()
        volume_url = submenu_item.a['href']
        volume_names.append(volume_name)
        volume_urls.append(volume_url)

    # Loop through the volume items to extract volume names and URLs
    for volume_item in volume_items:
        volume_name = volume_item.a.text.strip()
        volume_url = volume_item.a['href']
        volume_names.append(volume_name)
        volume_urls.append(volume_url)

    # Create a DataFrame using pandas
    data = {'Volume Name': volume_names, 'URL': volume_urls}
    df = pd.DataFrame(data)
    rows_to_remove = [4, 5, 6, 7, 8, 17, 18, 19, 20]  # Indices of rows to remove
    df = df.drop(rows_to_remove)
    df.reset_index(drop=True, inplace=True)
    complete_data=[]
    for index, row in df.iterrows():
        if index < 4:
            volume_name_cl = row['Volume Name']
            issue_number=volume_name_cl.split()[-1]
            volume_url = row['URL']
            issue_content=get_soup(volume_url,headers)
            if issue_content is None:
                continue
            entries = issue_content.find_all('div', class_='entry-content-wrap')

            for entry in entries:
                try:
                    # Extracting the date
                    date_element = entry.find('time', class_='entry-date published')
                    date = date_element.get_text()
                except (AttributeError, KeyError):
                    date = ''
                try:
                    if date is not None:
                        year = date.split(", ")[-1]
                except(AttributeError, KeyError):
                    year = ''

                # Extracting the title
                try:
                    title_element = entry.find('h2', class_='entry-title')
                    title = abstract_cleaner(title_element.a)
                except (AttributeError, KeyError):
                    title=''

                # Extracting the URL
                try:

                    url_element = entry.find('a', class_='post-more-link')
                    url = url_element['href']
                except (AttributeError, KeyError):
                    url=''

                article_content=get_soup(url,headers)
                if article_content is None:
                    continue
                try:
                    author_name = article_content.find('div', class_='entry-content single-content').find('p').text.replace(',', ';')
                except (AttributeError, KeyError):
                    author_name=''
                try:
                    abstract_Cl = article_content.find('div', class_='entry-content single-content').find_next('br').next_sibling
                    abstract=abstract_cleaner(abstract_Cl)
                except(AttributeError, KeyError):
                    abstract=''
                try:

                    full_text_link = article_content.find('a', class_='wp-block-file__button')['href']
                except(AttributeError,KeyError):
                    full_text_link=''
                print('current datetime------>', datetime.now())

                complete_data.append({
                    "journalname": journal_name,
                    "journalabbreviation": "",
                    "journalurl": journal_url,
                    "year": year,
                    "issn": ISSN,
                    "volume": volume_name_cl,
                    "issue": issue_number,
                    "articletitle": title,
                    "doiurl": '',
                    "author": author_name,
                    "author_affiliation": '',
                    "abstractbody": abstract,
                    "keywords": '',
                    "fulltext": '',
                    "fulltexturl": full_text_link,
                    "publisheddate": date,
                    "conflictofinterests": "",
                    "otherurl": '',
                    "articleurl": url,
                    "pubmedid": "",
                    "pmcid": "",
                    "sponsors": '',
                    "manualid": "",
                    "country": "",
                    "chemicalcode": "",
                    "meshdescriptioncode": "",
                    "meshqualifiercode": "",
                    "medlinepgn": "",
                    "language": "",
                    "nlmuniqueid": "",
                    "datecompleted": "",
                    "daterevised": '',
                    "medlinedate": "",
                    "studytype": "",
                    "isboolean": "",
                    "nativetitle": '',
                    "nativeabstract": '',
                    "citations": '',
                    "reference": '',
                    "disclosure": "",
                    "acknowledgements": '',
                    "supplement_url": ""

                })
        else:  # Process the remaining entries using the second method
            volume_name_cl = row['Volume Name']
            issue_number=volume_name_cl.split()[-1]
            volume_url = row['URL']
            issue_content = get_soup(volume_url, headers)
            if issue_content is None:
                continue
            entries = issue_content.find_all('div', class_='eael-entry-wrapper')

            # Loop through each entry and extract the required information
            for entry in entries:
                # Extract the date
                try:
                    date_element = entry.find('time', datetime=True)
                    date = date_element.get_text()
                except(AttributeError,KeyError):
                    date=''
                try:
                    if date is not None:
                        year = date.split(", ")[-1]
                except(AttributeError, KeyError):
                        year=''


                # Extract the title
                try:
                    title_element = entry.find('h2', class_='eael-entry-title')
                    title = abstract_cleaner(title_element.a)
                except(AttributeError, KeyError):
                    title=''
                # Extract the URL
                try:
                    url_element = entry.find('a', class_='eael-grid-post-link')
                    url = url_element['href']
                except(AttributeError, KeyError):
                    url=''
                article_content = get_soup(url, headers)
                if article_content is None:
                    continue
                try:

                    author_name = article_content.find('div', class_='entry-content single-content').find('p').text.replace(
                    ',', ';')
                except(AttributeError, KeyError):
                    author_name=''
                try:

                    full_text_link = article_content.find('a', class_='wp-block-file__button')['href']
                except(AttributeError, KeyError):
                    full_text_link=''
                try:
                    abstract_Cl = article_content.find('div', class_='entry-content single-content').find_next('br').next_sibling
                    abstract=abstract_cleaner(abstract_Cl)
                except(AttributeError, KeyError):
                    abstract=''
                print('current datetime------>', datetime.now())
                # Append the data to the list
                complete_data.append({
                    "journalname": journal_name,
                    "journalabbreviation": "",
                    "journalurl": journal_url,
                    "year": year,
                    "issn": ISSN,
                    "volume": volume_name_cl,
                    "issue": issue_number,
                    "articletitle": title,
                    "doiurl": '',
                    "author": author_name,
                    "author_affiliation": '',
                    "abstractbody": abstract,
                    "keywords": '',
                    "fulltext": '',
                    "fulltexturl": full_text_link,
                    "publisheddate": date,
                    "conflictofinterests": "",
                    "otherurl": '',
                    "articleurl": url,
                    "pubmedid": "",
                    "pmcid": "",
                    "sponsors": '',
                    "manualid": "",
                    "country": "",
                    "chemicalcode": "",
                    "meshdescriptioncode": "",
                    "meshqualifiercode": "",
                    "medlinepgn": "",
                    "language": "",
                    "nlmuniqueid": "",
                    "datecompleted": "",
                    "daterevised": '',
                    "medlinedate": "",
                    "studytype": "",
                    "isboolean": "",
                    "nativetitle": '',
                    "nativeabstract": '',
                    "citations": '',
                    "reference": '',
                    "disclosure": "",
                    "acknowledgements": '',
                    "supplement_url": ""

                })
    complete_data_df = pd.DataFrame(complete_data)
    if os.path.isfile(f'{JOURNAL_NAME}.csv'):
        complete_data_df.to_csv(f'{JOURNAL_NAME}.csv', index=False, header=False,
                           mode='a')
    else:
        complete_data_df.to_csv(f'{JOURNAL_NAME}.csv', index=False)
    write_visited_log(url)


