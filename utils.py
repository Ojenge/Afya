import requests
import jinja2
from xml.etree import ElementTree
from nltk import word_tokenize, pos_tag
from difflib import SequenceMatcher


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def search_disease(text):
    response = None
    result = search_medline(text)
    if result:
        response = result
    return response

def search_medline(text):
    body = ""
    nouns = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('N')]
    print nouns
    query_text = ""
    for item in nouns:
        query_text = query_text + " " + item
    print query_text
    if query_text is "":
        foreign = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('FW')]
        for item in foreign:
            query_text = query_text + " " + item
    print "now the payload"
    payload = {'db':'healthTopics','term': query_text}
    try:
        req = requests.get("https://wsearch.nlm.nih.gov/ws/query", params=payload)
        tree = ElementTree.fromstring(req.content)
        if tree[2].tag == 'spellingCorrection':
            correction = tree[2].text
            query = ""
            mytags = pos_tag(word_tokenize(text))
            words = tuple(x[0] for x in mytags)
            similar_words = []
            for word in words:
                score = similar(word,correction)
                if score > 0.9:
                    text = text.replace(word,correction)
                    similar_words.append(word)
            body = search_disease(text)
        rank = tree.find( './/*[@rank="0"]' )
        content = rank.find('.//*[@name="FullSummary"]')
        content = jinja2.filters.do_striptags(content.text)
        lines = content.split('.')
        definition = lines[:2]
        for item in definition:
            body = body + item + "."
    except:
        pass
    return body
