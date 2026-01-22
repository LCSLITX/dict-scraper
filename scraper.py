"Web scraper to gather the most used italian words from an online dictionary."

import json
import time
import re
import itertools
import string
import os
import requests

from bs4 import BeautifulSoup

BASE_URL = "https://dizionario.internazionale.it"
SEARCH_URL = "https://dizionario.internazionale.it/cerca/"

# Marche d'uso richieste: Fondamentale (FO), Alto Uso (AU), Alta Disponibilità (AD),
# Comune (CO), Basso Uso (BU), Obsoleto (OB)
ALLOWED_MARKS = {"FO", "AU", "AD", "CO", "BU", "OB"}

def get_soup(url):
    """Recupera il contenuto HTML di una URL e restituisce un oggetto BeautifulSoup."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error at {url}: {e}")
        with open('V2_scraping_errors_log.txt', 'a', encoding='utf-8') as l:
            l.write(f"ERROR: {url} | {e}\n")
        return None

def parse_word_page(url):
    """Estrae i dettagli di una parola dalla sua pagina dedicata."""
    soup = get_soup(url)
    if not soup:
        return None

    data = {
        "url": url,
        "id": url.split('/')[-1],
        "lemma": "",
        "display_lemma": "",
        "grammatical_category": "",
        "etymology": "",
        "usage_marks": [],
        "definitions": []
    }

    h1 = soup.find('h1')
    if not h1:
        return None

    data["display_lemma"] = h1.get_text(strip=True)
    sections = h1.find_all_next('section')

    if len(sections) < 1:
        with open('polirematiche.txt', "a", encoding="utf-8") as log:
            d = data["display_lemma"]
            log.write(f"{d} | {url}\n")
        return None

    if len(sections) >= 1:
        data["lemma"] = sections[0].get_text(strip=True)
    if len(sections) >= 2:
        data["grammatical_category"] = sections[1].get_text(strip=True)
    if len(sections) >= 3:
        data["etymology"] = sections[2].get_text(strip=True)

    if len(sections) >= 4:
        content = sections[3]

        # Estrazione Marca d'uso
        usage_tags = content.css.select('.mu')
        print(usage_tags)

        if usage_tags:
            ts = []
            for tag in usage_tags:
                t = tag.get_text(strip=True)
                ts.append(t)
            usage_marks = list(dict.fromkeys(ts))
            data["usage_marks"] = ", ".join(usage_marks)
        else:
            usage_marks = ["NOT_FOUND"]
            data["usage_marks"] = usage_marks

        print(usage_marks)
        # Estrazione Definizioni
        text_content = content.get_text("\n", strip=True)
        if usage_marks is not None:
            for mark in usage_marks:
                if text_content.startswith(mark):
                    text_content = text_content[len(mark):].strip()

        def_parts = re.split(r'(\d+[a-z]?\.\s)', text_content)
        if len(def_parts) > 1:
            if def_parts[0].strip():
                data["definitions"].append(
                        {"number": "0", "text": def_parts[0].strip().replace("\n", " ")}
                    )
            for i in range(1, len(def_parts), 2):
                num = def_parts[i].strip().replace(".", "")
                text = def_parts[i+1].strip().replace("\n", " ")
                data["definitions"].append({"number": num, "text": text})
        elif text_content:
            data["definitions"].append({"number": "1", "text": text_content.replace("\n", " ")})

    return data

def search_wildcard(query):
    """Esegue una ricerca con wildcard e restituisce i link filtrati per marca d'uso."""
    url = f"{SEARCH_URL}{query}"
    soup = get_soup(url)
    if not soup:
        return []

    results = []
    # I risultati della ricerca sono link che contengono '/parola/'
    all_links = soup.find_all('a', href=re.compile(r'/parola/'))

    for link_tag in all_links:
        href = link_tag['href']
        if not href.startswith('http'):
            href = BASE_URL + href

        parent = link_tag.parent
        context_text = parent.get_text() if parent else ""

        # Estrai le marche d'uso dal contesto
        found_marks = set(re.findall(r'\b(FO|AU|AD|CO|BU|OB)\b', context_text))

        if found_marks.intersection(ALLOWED_MARKS):
            results.append({
                "lemma": link_tag.get_text(strip=True),
                "url": href,
                "marks": list(found_marks.intersection(ALLOWED_MARKS))
            })

    return results

def generate_combinations(length=3):
    """Genera combinazioni di lettere (aaa, aab, aac, ...,zzx, zzy, zzz)."""
    chars = string.ascii_lowercase
    for combo in itertools.product(chars, repeat=length):
        yield "".join(combo)

def main():
    """Main function to execute the web scraper"""
    output_file = "DICTIONARY.jsonl"
    processed_urls = set()

    # Carica URL già processati se il file esiste
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    processed_urls.add(data['url'])
                except:
                    continue

    print("Inizio scraping...")
    
    # Iterazione da aaa* a zzz*
    for combo in generate_combinations(3):
        with open('scraping_log.txt', "a", encoding="utf-8") as log:
            query = combo + "*"
            str_1 = f"\n--- Elaborazione query: {query} ---"
            log.write(str_1 + "\n")
            print(str_1)

            words_to_scrape = search_wildcard(query)
            str_2 = f"Trovate {len(words_to_scrape)} parole corrispondenti ai criteri."
            log.write(str_2 + "\n")
            print(str_2)

            for word_info in words_to_scrape:
                if word_info['url'] in processed_urls:
                    continue

                str_3 = f"Scraping: {word_info['marks']} | {word_info['lemma']} ({word_info['url']})"
                log.write(str_3 + "\n")
                print(str_3)

                details = parse_word_page(word_info['url'])
                if details:
                    with open(output_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(details, ensure_ascii=False) + "\n")
                    processed_urls.add(word_info['url'])

                time.sleep(1) # Rispetto per il server

if __name__ == "__main__":
    main()
