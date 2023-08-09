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
        'Cache-Control': 'max-age=0',
        'Cookie': 'PHPSESSID=qbb1ofmsljd0hskru543hkauq3',
        'Referer': 'https://are-journal.com/are',
        'Sec-Ch-Ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    JOURNAL_NAME = os.path.basename(__file__).rstrip('.py')
    BASE_URL = 'https://archivosdemedicinadeldeporte.com'
    src_url = 'https://archivosdemedicinadeldeporte.com/en/'
    print('processing journal url----> ', src_url)
    journal_soup = get_soup(src_url, headers)
    journal_name = 'Archivos de Medicina del Deporte'
    journal_url = src_url
    year_divs = journal_soup.find_all('div', class_='caj-cal')

    # Iterate through each year div and extract the year text
    for year_div in year_divs:
        year_text = year_div.find('h2').text
        volumes = journal_soup.find_all("div", class_="caj-mes")
        if not volumes:
            print("No volumes found.")
        else:
            for volume in volumes:
                volume_link = volume.find("a")['href']
                volume_link= BASE_URL + volume_link
                volume_soup=get_soup(volume_link,headers)
                if volume_soup is None:
                    continue
                volume_content = volume_soup.find('div',class_='caj-boletin')
                volume_name = volume_content.find('h1').text.strip()
                # Define a regular expression pattern to match the volume and issue number
                pattern = r'(\d+)VOLUMEN (\d+)\s*(?:\(Supl\. (\d+)\)|\((\d+)\))?'
                # Search for the pattern in the text
                match = re.search(pattern, volume_name)

                if match:
                    volume_name_fin = f"VOLUMEN {match.group(2)}"
                    issue_number = match.group(3) or match.group(4)
                else:
                    volume_name_fin=''
                    issue_number=''

                articles=volume_content.find_all('h3',class_="titulo-es ck74")
                for article in articles:
                    try:
                        article_name = abstract_cleaner(article.find('a'))
                    except (AttributeError,KeyError):
                        article_name=''
                    try:
                        article_url= BASE_URL + '/' + article.find('a')['href']

                    except (AttributeError,KeyError):
                        article_url=''

                    try:
                        full_text_link = article.find_next('li', class_='fichero-articulo').a
                        if full_text_link:
                            full_text_url = BASE_URL + '/' + full_text_link['href']
                        else:
                            full_text_url = None
                    except (AttributeError,KeyError):
                        full_text_url=''

                    article_content=get_soup(article_url,headers)

                    article_containers = article_content.find_all('div', class_='caj-boletin')

                    # Initialize lists to store scraped data
                    authors = ''
                    summary_texts = ''

                    for container in article_containers:
                        # Find author name
                        try:
                            author_element = container.find('p')
                            if author_element:
                                if author_element:
                                    author_name = author_element.get_text(strip=True)
                        except:
                            author_name=''

                        # Find summary text
                        try:

                            summary_element = container.find('div', class_='fadetext')
                            if summary_element:
                                summary_text = abstract_cleaner(summary_element)
                            else:
                                summary_text=None
                        except:
                            summary_text=''
                        print(year_text)

                # print('current datetime------>', datetime.now())
                # dictionary = {
                #     "journalname": journal_name,
                #     "journalabbreviation": "",
                #     "journalurl": journal_url,
                #     "year": year_el,
                #     "issn": '',
                #     "volume": volume_name_fin,
                #     "issue": issue_number,
                #     "articletitle": article_name,
                #     "doiurl": '',
                #     "author": author_name,
                #     "author_affiliation": '',
                #     "abstractbody": summary_text,
                #     "keywords": '',
                #     "fulltext": '',
                #     "fulltexturl": full_text_url,
                #     "publisheddate": '',
                #     "conflictofinterests": "",
                #     "otherurl": '',
                #     "articleurl": article_url,
                #     "pubmedid": "",
                #     "pmcid": "",
                #     "sponsors": '',
                #     "manualid": "",
                #     "country": "",
                #     "chemicalcode": "",
                #     "meshdescriptioncode": "",
                #     "meshqualifiercode": "",
                #     "medlinepgn": "",
                #     "language": "",
                #     "nlmuniqueid": "",
                #     "datecompleted": "",
                #     "daterevised": '',
                #     "medlinedate": "",
                #     "studytype": "",
                #     "isboolean": "",
                #     "nativetitle": '',
                #     "nativeabstract": '',
                #     "citations": '',
                #     "reference": '',
                #     "disclosure": "",
                #     "acknowledgements": '',
                #     "supplement_url": ""
                # }
                # articles_df = pd.DataFrame([dictionary])
                # if os.path.isfile(f'{JOURNAL_NAME}.csv'):
                #     articles_df.to_csv(f'{JOURNAL_NAME}.csv', index=False, header=False,
                #                        mode='a')
                # else:
                #     articles_df.to_csv(f'{JOURNAL_NAME}.csv', index=False)
                # write_visited_log(article_url)
