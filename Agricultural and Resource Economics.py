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
        'Cookie': 'OJSSID=485d9e50df896a06beff2a0036c202df',
        'Referer': 'https://are-journal.com/are',
        'Sec-Ch-Ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
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
    BASE_URL = 'https://are-journal.com/are'
    src_url = 'https://are-journal.com/are/issue/archive'
    print('processing journal url----> ', src_url)
    journal_soup = get_soup(src_url, headers)
    journal_name = 'Agricultural and Resource Economics'
    journal_url = src_url
    issn_number = '2414-584X'
    # Start scraping from page 1
    current_page = 1
    while True:
        page_content = get_next_page(src_url, current_page, headers)
        if page_content is None:
            print("Failed to fetch the page or reached the end.")
            # Failed to fetch the page, so break the loop
            break

        volumes = page_content.find_all("div", class_="obj_issue_summary")
        if not volumes:
            break
        else:
            for volume in volumes:
                volume_name_complete = volume.find("a", class_="title").text.strip()
                volume_link=volume.find("a",class_="cover")['href']
                # Split volume_name_complete to get vol_name_and_issue
                vol_name_and_issue, _ = volume_name_complete.split(' (', 1)
                # Use regular expression to capture volume name (Vol 1) and issue name (No 4)
                match = re.match(r'(Vol \d+) (No \d+)', vol_name_and_issue)
                if match:
                    vol_name, issue_name = match.group(1), match.group(2)
                else:
                    # If the regular expression doesn't match, handle the error or use default values
                    vol_name, issue_name = None, None

                year = volume_name_complete[-5:-1]
                issue_soup = get_soup(volume_link, headers)
                if issue_soup is None:
                    continue
                articles = issue_soup.find_all('div', class_='obj_article_summary')
                for article in articles:
                    try:
                        article_name = abstract_cleaner(article.find('div', class_='title'))
                    except AttributeError:
                        article_name = ''

                    try:
                        article_url = article.find('div', class_='title').find('a')['href']
                    except (AttributeError, KeyError):
                        article_url = ''

                    try:
                        DOI = article.find('div', class_='item doi').find('a')['href']
                    except (AttributeError, KeyError):
                        DOI = ''

                    try:
                        fulltexturl = article.find('a', class_='obj_galley_link pdf')['href']
                    except (AttributeError, KeyError):
                        fulltexturl = ''

                    article_content=get_soup(article_url,headers)
                    if article_content is None:
                        continue
                    article_body=article_content.find('article',class_='obj_article_details')

                    try:
                        author_names = [author.text.strip() for author in
                                        article_content.find('ul', class_='item authors').find_all('span', class_='name')]
                        authors_clean = ', '.join(map(str, author_names))
                        authors = authors_clean.replace(',', ';')
                    except AttributeError:
                        authors = ''

                    try:
                        keywords = article_content.find('div', class_='item keywords').find('span', class_='value')
                        keywords_=abstract_cleaner(keywords)
                        keywords_clean=keywords_.replace(',', ';')


                    except (AttributeError, KeyError):
                        keywords_clean = ''

                    try:
                        published = article_content.find('div',class_='item published').find('div', class_='value').text.strip()
                    except (AttributeError, KeyError):
                        published = ''

                    try:
                        references_list = []
                        for reference in article_content.select(".item.references .value p"):
                            reference_cl=abstract_cleaner(reference)
                            references_list.append(reference_cl)

                        references = "; ".join(references_list)

                    except:
                        references = ''

                    try:
                        
                        abstractbody = ''.join(
                            [abstract_cleaner(p) for p in article_content.find('div', class_='item abstract').find_all('p')])

                    except:
                        abstractbody = ''

                    try:
                        affiliation_elements = article_content.find_all('span', class_='affiliation')

                        # Extract the text content of the affiliation_elements
                        affiliations_list = []
                        for elem in affiliation_elements:
                            if not elem.find('a'):
                                text = elem.get_text(strip=True)
                                affiliations_list.append(text)

                        affiliations_list_clean = ', '.join(map(str, affiliations_list))

                        affiliations = affiliations_list_clean.replace(',', ';')

                    except:
                        affiliations = ''

                    try:
                        div_csl_entry = article_content.find('div', class_='csl-entry')
                        content = div_csl_entry.get_text()
                        citation=content.strip()
                    except:
                        citation = ''

                    try:
                        other_urls=[elem.find('a')['href'] for elem in article_content.find_all('span', class_='affiliation').find_all('a')]
                    except:
                        other_urls = ''
                    print('current datetime------>', datetime.now())
                    dictionary = {
                        "journalname": journal_name,
                        "journalabbreviation": "",
                        "journalurl": journal_url,
                        "year": year,
                        "issn": issn_number,
                        "volume": vol_name,
                        "issue": issue_name,
                        "articletitle": article_name,
                        "doiurl": DOI,
                        "author": authors,
                        "author_affiliation": affiliations,
                        "abstractbody": abstractbody,
                        "keywords": keywords_clean,
                        "fulltext": '',
                        "fulltexturl": fulltexturl,
                        "publisheddate": published,
                        "conflictofinterests": "",
                        "otherurl": other_urls,
                        "articleurl": article_url,
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
                        "citations": citation,
                        "reference": references,
                        "disclosure": "",
                        "acknowledgements": '',
                        "supplement_url": ""
                    }
                    articles_df = pd.DataFrame([dictionary])
                    if os.path.isfile(f'{JOURNAL_NAME}.csv'):
                        articles_df.to_csv(f'{JOURNAL_NAME}.csv', index=False, header=False,
                                           mode='a')
                    else:
                        articles_df.to_csv(f'{JOURNAL_NAME}.csv', index=False)
                    write_visited_log(article_url)

        # Increment to the next page
        current_page += 1

