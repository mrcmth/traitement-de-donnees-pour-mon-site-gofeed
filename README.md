# Je vous présente les grandes lignes du fonctionnement de mon site gofeed.fr

Cette présentation se scinde en 3 parties :

1. Partie 1 (Python) qui se concentre sur l'extraction, le traitement et l'envoie de l'article de presse à la base de donnée.
2. Partie 2 (Php/Mysql) qui montre comment j'organise la gestion des données et l'affichage sur le site

## Partie 1, traitement de données : 

1. "Scraping" des articles de presses, dans notre cas je vous montre comment j'ai fais pour le site leprogres.fr

  1.1 INTRO :

Tout d'abord, on explore la page d'accueil du Progres dédié à la Haute-Loire et on extrait tous les liens des articles avec le module beautiful soup

```python
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
```
On trie les liens, en effet ceux commençant par https://boutique. sont des articles publicitaires, donc pas intérressant à scraper.

```python
            if "https://boutique." not in article_link:
                article_links.append(article_link)

```

et pour chaque articles déniché, on commence le traitement.

```python
    for link in article_links:
        print(f"\nExtracting information for article: {link}")
        extract_information(link)
```

1.2 **Le vif du sujet**

Le **traitement** consiste à récupérer différentes composantes des articles pour que je puisse les intégrer sur mon site, cela passe par le traitement d'image à la détermination du sujet:

J'insère 7 éléments par articles dans ma base de donnée : 

élément 1 : le journal, rien d'exceptionnel
```python
    journal = "actu_leprogres"
```

élément 2 et 3 : titre et description
simplement extrait via beautiful soup

```python
   title = ' '.join(article.find('h1').text.split()).strip()
        journal = "actu_leprogres"
        description_elements = article.find_all('div', class_='textComponent')
        description = '\n'.join([element.text.strip() for element in description_elements])
```

élément 4 : Les mots clés ! 

extract_keywords() se sert d'un fichier json (que je vous mets en annexe : motCle.json) pour déterminer les mots clés d'un articles. Il prend en entré le contenu textuel de l'article.

Exemple : "Marc aimerait travailler dans le domaine de l'informatique. Pour cela il postule dans différents masters via la platefome monMaster"

--> Dans le json, il y a les mots "travailler", "postuler" qui sont relié au mot clé : "professionnel". Il y a aussi les mots "master" et "monMaster" relié au mot clé "enseignement supérieur". Donc on a 2 mots clés pour cet article, ainsi si on remarque qu'un utilisateur lit beaucoup d'article sur l'éducation, le monde du travail, alors il est pertinent de lui proposer cet article.

```python

text_content = title + " " + description
 keywords = extract_keywords(text_content)

def extract_keywords(text):
    with open(r"mc.json", 'r') as fichier:
        keywords = json.load(fichier)

    keyword_set = set(keywords.keys())

    nlp = spacy.load("fr_core_news_sm")

    cleaned_text = text.lower().translate(str.maketrans("", "", string.punctuation))
    normalized_text = unidecode(cleaned_text)

    words_in_text = normalized_text.split()

    found_keywords = {}

    for word in words_in_text:
        lemma = nlp(word)[0].lemma_

        if word in keyword_set:
            found_keywords[word] = keywords[word]
        elif lemma in keyword_set:
            found_keywords[lemma] = keywords[lemma]

    print(len(found_keywords))
    sujet = pourcentage_categorie(found_keywords)
    print(sujet)

    return found_keywords, sujet
```
On a un appel au mc.json qui est le fichier json utilisé, j'utlise aussi des techniques de lemmatisation pour le traitement des mots. ex : "chevronné" est transformé en "chevronne" pour corroborer avec les données du json. 

ex de print de la fonction : 

```
sujet probable :  ('economie', 33.333333333333336)
Catégorie culture: 0.00 %
Catégorie economie: 33.33 %
Catégorie divers: 0.00 %
Catégorie ville: 8.33 %
Catégorie sport: 8.33 %
Catégorie faitsDivers: 0.00 %
Catégorie lieu: 16.67 %
Catégorie meteo: 25.00 %
Catégorie societe: 8.33 %
```

Le "sujet probable" me permet de déterminer la dominante de l'article pour pouvoir le classer dans une catégorie spéciale de mon site.

élément 5 : on traite l'image de l'article en enlevant le fond blanc, en compressant l'image, en générant une nouvelle adresse http de l'image car cette image est stockée dans mes propres serveurs. L'image traitée est donc directement téléversée en ssh à la db, seul le lien généré est inséré à la table sql.

```python
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

```

Traitement de l'image : dispo en annexe

et les éléments 6 et 7 dont l'heure et la date d'extraction.
