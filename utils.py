import requests
import jinja2
import json
import re
from xml.etree import ElementTree
from nltk import word_tokenize, pos_tag
from difflib import SequenceMatcher
from lxml import etree

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def search_disease(text):
    response = None
    result = search_afyarestinfo(text)
    if result is None:
        result = search_medline(text)
    if result:
        response = result
    return response

def disease_symptoms(text):
    response = None
    result = search_afyarest_symptoms(text)
    if result is None:
        result = search_medline_symptoms(text)
    if result:
        response = result
    return response

def disease_treatment(text):
    response = None
    result = search_afyarest_treatment(text)
    if result is None:
        result = search_medline_treatment(text)
    if result:
        response = result
    return response


def search_ctakes_disorder(root,begin,end):
    disease = None
    nsmap = {k:v for k,v in root.nsmap.iteritems() if k}
    words = root.findall('syntax:TerminalTreebankNode', nsmap)
    for word in words:
        if word.get('begin') == begin and word.get('end') == end:
            disease = word.get('nodeValue')
    return disease


def get_disorder_ctakes(text):
    data = {'q': text, 'format':'xml'}
    disease=None
    try:
        r = requests.post("http://52.27.22.206:8080/DemoServlet", data=data)
        tree = etree.fromstring(r.content)
        tree = etree.ElementTree(tree)
        root = tree.getroot()
        nsmap = {k:v for k,v in root.nsmap.iteritems() if k}
        disorder = root.findall('textsem:DiseaseDisorderMention',nsmap)
        if disorder:
            for item in disorder:
                begin = item.get('begin')
                end = item.get('end')
                disease = search_ctakes_disorder(root,begin,end)
    except:
        pass
    return disease

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

def search_medline_symptoms(text):
    body = ""
    nouns = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('N')]
    regex = re.compile(".*(symptoms).*",re.IGNORECASE)
    search = [m.group(0) for l in nouns for m in [regex.search(l)] if m]
    if len(search) == 0 :
        nouns.append("symptoms")
    query_text = ""
    for item in nouns:
        query_text = query_text + " " + item
    payload = {'db':'healthTopics','term': query_text}
    try:
        req = requests.get("https://wsearch.nlm.nih.gov/ws/query", params=payload)
        tree = ElementTree.fromstring(req.content)
        rank = tree.find( './/*[@rank="0"]' )
        content = rank.find('.//*[@name="FullSummary"]')
        content = jinja2.filters.do_striptags(content.text)
        symptom = re.search('symptoms',content, re.IGNORECASE)
        if symptom:
            sentence = re.findall(r"([^.]*?symptoms[^.]*\.)",content, re.IGNORECASE)
            body = sentence[0]
    except:
        pass
    return body

def search_medline_treatment(text):
    body = ""
    nouns = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('N')]
    regex = re.compile(".*(treat).*",re.IGNORECASE)
    search = [m.group(0) for l in nouns for m in [regex.search(l)] if m]
    if len(search) == 0 :
        nouns.append("treat")
    query_text = ""
    for item in nouns:
        query_text = query_text + " " + item
    payload = {'db':'healthTopics','term': query_text}
    try:
        req = requests.get("https://wsearch.nlm.nih.gov/ws/query", params=payload)
        tree = ElementTree.fromstring(req.content)
        rank = tree.find( './/*[@rank="0"]' )
        content = rank.find('.//*[@name="FullSummary"]')
        content = jinja2.filters.do_striptags(content.text)
        treat = re.search('treat',content, re.IGNORECASE)
        if treat:
            sentence = re.findall(r"([^.]*?treat[^.]*\.)",content, re.IGNORECASE)
        else:
            sentence = re.findall(r"([^.]*?cure[^.]*\.)",content, re.IGNORECASE)
        body = sentence[0]
    except:
        pass
    return body

def search_afyarestinfo(text):
    body = None
    if get_disorder_ctakes(text):
        query_text = get_disorder_ctakes(text)
    else:
        nouns = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('N')]
        query_text = ""
        for item in nouns:
            query_text = query_text + " " + item
        if query_text is "":
            foreign = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('FW')]
            for item in foreign:
                query_text = query_text + " " + item
    request = requests.post('http://afyarest.herokuapp.com/search', data = {'querytype': 'diseaseinfo', 'query': query_text})
    result = json.loads(request.content)
    try:
        body = result[0]['fields']['diseaseinfo']
    except:
        body
    return body

def search_afyarest_symptoms(text):
    body = None
    if get_disorder_ctakes(text):
        query_text = get_disorder_ctakes(text)
    else:
        nouns = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('N')]
        query_text = ""
        for item in nouns:
            query_text = query_text + " " + item
        if query_text is "":
            foreign = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('FW')]
            for item in foreign:
                query_text = query_text + " " + item
    request = requests.post('http://afyarest.herokuapp.com/search', data = {'querytype': 'diseasesymptoms', 'query': query_text})
    result = json.loads(request.content)
    try:
        body = result[0]['fields']['diseasesymptoms']
    except:
        body
    return body

def search_afyarest_treatment(text):
    body = None
    if get_disorder_ctakes(text):
        query_text = get_disorder_ctakes(text)
    else:
        nouns = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('N')]
        query_text = ""
        for item in nouns:
            query_text = query_text + " " + item
        if query_text is "":
            foreign = [token for token, pos in pos_tag(word_tokenize(text)) if pos.startswith('FW')]
            for item in foreign:
                query_text = query_text + " " + item
    request = requests.post('http://afyarest.herokuapp.com/search', data = {'querytype': 'diseasecure', 'query': query_text})
    result = json.loads(request.content)
    try:
        body = result[0]['fields']['diseasetreat']
    except:
        body
    return body
