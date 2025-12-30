"""A scraper to collect data from a specific dictionary website."""

import re
import time
import json

import requests
from tabulate import tabulate
from bs4 import BeautifulSoup


BASE_URL = "https://dizionario.internazionale.it"


def get_soup(url):
    """Gather content HTML of an URL and returns a BeautifulSoup object."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print("URL: ", response.url)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error at {url}: {e}")
        return None


def parse_word_page(url):
    """Extract the details of a word from its dedicated page."""
    soup = get_soup(url)
    if not soup:
        return None

    data = {
        "url": url,
        "id": url.split('/')[-1],
        "word": url.split('/')[-1].split('_')[0],
        "lemma": "",
        "display_lemma": "",
        "grammatical_category": "",
        "etymology": "",
        "usage_marks": "",
        "definitions": []
    }

    h1 = soup.find('h1')
    if not h1:
        return None

    data["display_lemma"] = h1.get_text(strip=True)

    # La struttura del sito utilizza tag <section> per i diversi blocchi di dati
    sections = h1.find_all_next('section')

    if len(sections) >= 1:
        data["lemma"] = sections[0].get_text(strip=True)
    if len(sections) >= 2:
        data["grammatical_category"] = sections[1].get_text(strip=True)
    if len(sections) >= 3:
        data["etymology"] = sections[2].get_text(strip=True)

    if len(sections) >= 4:
        content = sections[3]

        # Estrazione Marca d'uso
        usage_tags = content.find_all('abbr')
        if usage_tags:
            usage_marks = [tag.get_text(strip=True) for tag in usage_tags]
            data["usage_marks"] = ", ".join(usage_marks)

        # Estrazione Definizioni
        text_content = content.get_text("\n", strip=True)
        for mark in usage_marks:
            if text_content.startswith(mark):
                text_content = text_content[len(mark):].strip()
        # if data["usage_mark"] and text_content.startswith(data["usage_mark"]):
        #     text_content = text_content[len(data["usage_mark"]):].strip()

        # Regex per identificare l'inizio delle definizioni numerate (es. "1. ", "5a. ")
        def_parts = re.split(r'(\d+[a-z]?\.\s)', text_content)

        if len(def_parts) > 1:
            if def_parts[0].strip():
                data["definitions"].append({"number": "0", "text": def_parts[0].strip().replace("\n", " ")})
            for i in range(1, len(def_parts), 2):
                num = def_parts[i].strip().replace(".", "")
                text = def_parts[i+1].strip().replace("\n", " ")
                data["definitions"].append({"number": num, "text": text})
        elif text_content:
            data["definitions"].append({"number": "1", "text": text_content.replace("\n", " ")})

    return data


def get_word_links_from_letter(letter, max_pages=None):
    """Obtains all the links to the words for a specific letter, managing the pagination."""
    links = []
    page = 1
    uppercase_letter = letter.upper()

    while True:
        if max_pages and page > max_pages:
            break

        url = f"{BASE_URL}/lettera/{letter}-{page}"
        print(f"Scanning content of letter '{uppercase_letter}', pagina {page}...")
        soup = get_soup(url)

        if not soup:
            break

        all_links = soup.find_all('a')
        page_links = []

        for link in all_links:
            href = link.get('href', '')
            if '/parola/' in href:
                if not href.startswith('http'):
                    href = BASE_URL + href
                if href not in page_links:
                    page_links.append(href)
                    print(href)

        if not page_links:
            break

        links.extend(page_links)
        page += 1
        print("page: ", page)
        time.sleep(0.5) # Breve pausa tra le pagine dell'elenco

    return list(dict.fromkeys(links))


def scrape_dictionary(letters=None, output_file="dict_complete.jsonl", generate_report=False, analysis=False):
    """Main function for scraping the entire dictionary or specific letters."""
    if not letters:
        letters = [chr(i) for i in range(ord('a'), ord('z') + 1)]

    print(f"Starting scraping for the letter: {', '.join(letters)}")

    report_file_name = f"report_{output_file.split('.')[0].split('_')[-1]}"
    report_haeders = ["Initial Letter", "Letter Index", "ID (link)", "Word"]
    data = []

    for letter in letters:
        uppercase_letter = letter.upper()
        word_links = get_word_links_from_letter(letter, max_pages=None)
        print(f"Found {len(word_links)} words for the letter '{uppercase_letter}'.")

        for i, link in enumerate(word_links):
            _id = link.split('/')[-1]
            word = _id.split('_')[0]
            line = [f"{uppercase_letter}", f"{i+1}/{len(word_links)}", f"{_id}", f"{word}"]
            data.append(line)

    if generate_report:
        with open(report_file_name, 'a', encoding='utf-8') as r:
            r.write(tabulate(data, headers=report_haeders, showindex="always", tablefmt="simple_outline"))

    if analysis:
        with open(output_file, 'a', encoding='utf-8') as f:
            for i, link in enumerate(word_links):
                print(f"[{uppercase_letter}] Analysis {i+1}/{len(word_links)}: {link}")
                word_data = parse_word_page(link)
                if word_data:
                    f.write(json.dumps(word_data, ensure_ascii=False) + "\n")
                time.sleep(1) # Rispetto per il server (Rate Limiting)

if __name__ == "__main__":
    scrape_dictionary(letters=['z'], output_file="dict_z.jsonl")
    # scrape_dictionary()
