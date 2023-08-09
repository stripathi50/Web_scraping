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
    url = f"{base_url}/page/{page_num}"
    return get_soup(url, headers)


# Function to remove square brackets from the text
def remove_square_brackets(text):
    # Find the index of the first '[' and the index of the last ']'
    start_index = text.find('[')
    end_index = text.rfind(']')

    # Return the text without the square brackets
    return text[start_index + 1:end_index]

def extract_volume_and_issue(volume_string):
    parts = volume_string.split('.')
    volume_name = parts[0].replace("Volume", "").strip()

    if len(parts) > 1:
        if "(" in parts[1]:
            issue_name = parts[1].split('(')[1].split(')')[0]
        elif "-" in parts[1]:
            issue_name = None
        else:
            issue_name = parts[1]
    else:
        issue_name = None

    return volume_name, issue_name

if __name__ == '__main__':
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'Cookie': 'PHPSESSID=2aegkog5kp4pp1a3vv87jrdru1db4ebi',
        'Referer': 'https://are-journal.com/are',
        'Sec-Ch-Ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"macOS"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    JOURNAL_NAME = os.path.basename(__file__).rstrip('.py')
    BASE_URL = 'https://www.ardeola.org'
    src_url = 'https://www.ardeola.org/en/volumes/'
    print('processing journal url----> ', src_url)
    journal_soup = get_soup(src_url, headers)
    journal_name = 'Ardeola'
    journal_url = src_url
    # Start scraping from page 1
    current_page = 1
    while True:
        page_content = get_next_page(src_url, current_page, headers)
        if page_content is None:
            print("Failed to fetch the page or reached the end.")
            # Failed to fetch the page, so break the loop
            break

        volumes = page_content.find_all("div", class_="book-list-meta")
        if not volumes:
            break
        else:
            for volume in volumes:

                volume_name_complete = volume.find("h3", class_="book-list-title").text.strip()
                volume_, issue_name = extract_volume_and_issue(volume_name_complete)
                volume_name="Volume " + volume_

                a_tag = volume.find('h3', class_='book-list-title').find('a')
                href_link = BASE_URL+a_tag['href']
                #issue_name =  """"""""""""""""""""""""""""""""""""yet to be done""""""""""""""""""""""""""""""
                issue_articles = get_soup(href_link,headers)
                if issue_articles is None:
                    continue
                articles = issue_articles.find_all("div",class_='journal-papers-meta')
                for article in articles:
                    try:
                        a_tag = article.find('a')
                        article_name = abstract_cleaner(a_tag)
                    except AttributeError:
                        article_name = ''
                    #"-------------------------Article Name----------------------------------"

                    try:
                        article_url=BASE_URL+article.find('a')['href']
                    except (AttributeError, KeyError):
                        article_url = ''

                    article_content=get_soup(article_url, headers)
                    if article_content is None:
                        continue
                    content_extract=article_content.find('div', class_='events-item-meta-text')
                    doi_url = ''
                    language = ''
                    keywords = ''
                    published_date = ''
                    year = ''
                    author_name = ''

                    for p_tag in content_extract.find_all('p'):
                        try:
                            if "Doi:" in p_tag.text:
                                doi_url = p_tag.a['href']
                        except (AttributeError, KeyError):
                            doi_url = ''

                        try:
                            if "Language:" in p_tag.text:
                                language = p_tag.get_text(strip=True).replace("Language:", "")

                        except (AttributeError, KeyError):
                            language = ''

                        try:
                            if "Keywords:" in p_tag.text:
                                keywords_list = p_tag.find_all('a', href=True)
                                keywords = abstract_cleaner(keywords_list)
                                clean_keywords = keywords.replace(',', ';')
                                keywords = clean_keywords.replace('[', '').replace(']', '')
                        except (AttributeError, KeyError):
                            keywords = ''

                        try:
                            if "Published:" in p_tag.text:
                                published_text = p_tag.get_text(strip=True).replace("Published:", "")
                                published_date = published_text.split(',')[-1].split('.')[0].strip()

                        except (AttributeError, KeyError):
                            published_date = ''

                        try:
                            if published_date:
                                year = published_date.split()[-1]

                        except (AttributeError, KeyError):
                            year = ''

                        try:
                            if "Authors:" in p_tag.text:
                                authors = p_tag.find_all('a', href=True)
                                author_name = '; '.join([author.get_text(strip=True) for author in authors])

                        except (AttributeError, KeyError):
                            author_name = ''

                    try:

                        fulltext_link = article_content.find('a', class_='pdf-link', href=True)
                        fulltext_url = fulltext_link['href'] if fulltext_link else None
                        if fulltext_url is not None:
                            fulltext_url = BASE_URL+fulltext_url
                        else:
                            fulltext_url = ''
                    except (AttributeError, KeyError):
                        fulltext_url = ''

                    try:
                        summary_tag = article_content.find('p', string="Summary:")
                        if summary_tag:
                            summary_clean = summary_tag.find_next_sibling('p')
                            if summary_clean:
                                try:
                                    summary = abstract_cleaner(summary_clean)
                                except (AttributeError, KeyError):
                                    summary = ''
                            else:
                                summary = ''
                        else:
                            summary = ''
                    except (AttributeError, KeyError):
                        summary = ''

                    try:
                        supplementary_link = article_content.find('p', string='Supplementary Material:')
                        supplementary_url = supplementary_link.find_next('a', class_='pdf-link')['href']
                        full_supplementary_url = BASE_URL + supplementary_url

                    except (AttributeError,KeyError):
                        full_supplementary_url = ''

                    print('current datetime------>', datetime.now())
                    dictionary = {
                        "journalname": journal_name,
                        "journalabbreviation": "",
                        "journalurl": journal_url,
                        "year": year,
                        "issn": '',
                        "volume": volume_name,
                        "issue": issue_name,
                        "articletitle": article_name,
                        "doiurl": doi_url,
                        "author": author_name,
                        "author_affiliation": '',
                        "abstractbody": summary,
                        "keywords": keywords,
                        "fulltext": '',
                        "fulltexturl": fulltext_url,
                        "publisheddate": published_date,
                        "conflictofinterests": "",
                        "otherurl": '',
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
                        "language": language,
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
                        "supplement_url": full_supplementary_url
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