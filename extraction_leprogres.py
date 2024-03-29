import requests
from bs4 import BeautifulSoup
import json
import string
import spacy
from unidecode import unidecode
import mysql.connector
from datetime import datetime
import random
import img_traitement
import insertion


def trouver_plus_haute_valeur(valeur_pourcentage):
    categorie_max, valeur_max = max(valeur_pourcentage.items(), key=lambda x: x[1])
    return categorie_max, valeur_max

def pourcentage_categorie(found_keywords):
    mots_par_categorie = {'culture': 0, 'economie': 0, 'divers': 0, 'ville': 0, 'sport': 0, 'faitsDivers': 0}
    total = len(found_keywords)

    for mot, categorie in found_keywords.items():
        if categorie in mots_par_categorie:
            mots_par_categorie[categorie] += 1
        else:
            mots_par_categorie[categorie] = 1

    # Afficher le résultat
    valeur_pourcentage = {}

    for categorie, nombre in mots_par_categorie.items():
        if total != 0:
            pourcentage = nombre * 100 / total
        else:
            pourcentage = 0
        valeur_pourcentage[categorie] = pourcentage

    # Afficher le résultat
    value_max = trouver_plus_haute_valeur(valeur_pourcentage)
    print("sujet probable : ", value_max)

    for categorie, pourcentage in valeur_pourcentage.items():
        print(f"Catégorie {categorie}: {pourcentage:.2f} %")

    return value_max

def extract_keywords(text):
    # Load keywords from an external file
    with open(r"mc.json", 'r') as fichier:
        keywords = json.load(fichier)

    # Convert keywords to a set for faster lookup
    keyword_set = set(keywords.keys())

    # Initialize the spaCy model for lemmatization
    nlp = spacy.load("fr_core_news_sm")

    # Clean and normalize the text
    cleaned_text = text.lower().translate(str.maketrans("", "", string.punctuation))
    normalized_text = unidecode(cleaned_text)

    # Split the text into words
    words_in_text = normalized_text.split()

    # Initialize a dictionary to store unique keywords and their categories
    found_keywords = {}

    # Compare words with the keyword set and add keywords with their categories
    for word in words_in_text:
        # Lemmatize the word
        lemma = nlp(word)[0].lemma_

        # Check if the word or its lemma is in the keyword list
        if word in keyword_set:
            found_keywords[word] = keywords[word]
        elif lemma in keyword_set:
            found_keywords[lemma] = keywords[lemma]

    print(len(found_keywords))
    sujet = pourcentage_categorie(found_keywords)
    print(sujet)

    return found_keywords, sujet

def extract_information(url):
 
    response = requests.get(url)

    if response.status_code == 200:
       
        soup = BeautifulSoup(response.content, 'html.parser')

      
        article = soup.find('article')

        title = ' '.join(article.find('h1').text.split()).strip()
        journal = "actu_leprogres"
        description_elements = article.find_all('div', class_='textComponent')
        description = '\n'.join([element.text.strip() for element in description_elements])
        image_s_link = None  

        illustration_div = article.find('div', class_='illustration')
        if illustration_div:
            image_tag = illustration_div.find('img')
            if image_tag and 'src' in image_tag.attrs:
                img_link = image_tag['src']
                image_s_link = "https://gofeed.fr" + img_traitement.remove_background_and_crop(img_link, journal)
            else:
                print("No image link found for this article.")
        else:
            print("No illustration div found for this article.")
        
        text_content = title + " " + description
        type = "text"
        heure = (datetime.now().time()).strftime('%H:%M:%S')
        trend_score = random.randint(0, 10)
        keywords = extract_keywords(text_content)
        date_published = datetime.today().strftime("%Y-%m-%d")

        insertion.insert_article(title, description, journal, url, type, date_published, heure, image_s_link, keywords, trend_score)

    else:
        print(f"Failed to fetch the webpage. Status code: {response.status_code}")

main_url = "https://www.leprogres.fr/haute-loire"
response = requests.get(main_url)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('article', class_='article')

    article_links = []

    for article in articles:
        article_link_tag = article.find('a', class_='article_content')
        if article_link_tag:
            article_link = "https://www.leprogres.fr" + article_link_tag.get('href')

            if "https://boutique." not in article_link:
                article_links.append(article_link)

    for link in article_links:
        print(f"\nExtracting information for article: {link}")
        extract_information(link)

else:
    print("Failed to fetch the main webpage. Status code:", response.status_code)
