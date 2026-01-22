"""Parser"""

import json
import re


def parse_to_wordlist():
    """Get the scraper result file and parse it in a simple wordlist."""
    wordlist = []

    with open("./DICTIONARY.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                word_with_number = f"{data['display_lemma']}\n"
                word_without_numbers = re.sub(r'\d+', '', word_with_number)
                wordlist.append(word_without_numbers)
            except:
                continue

    wordlist = list(dict.fromkeys(wordlist))

    with open("WORDLIST", "a", encoding="utf-8") as wl:

        for word in wordlist:
            try:
                wl.write(f"{word}")
                print(word)
            except:
                wl.write("ERROR")


def get_maximum_length():
    """Get the maximum word length in the wordlist."""
    with open("./DICTIONARY.jsonl", "r", encoding="utf-8") as wl:
        length = 0

        for word in wl:
            l = len(word)
            length = max(length, l)

    print(f"maximum length is: {length}")


get_maximum_length()
