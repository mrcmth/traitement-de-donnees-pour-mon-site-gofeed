# Je vous présente les grandes lignes du fonctionnement de mon site gofeed.fr

//// ATTENTION : La barre de recherche dans le header ne fonctionne pas dans la version mobile (problème de javascript), elle est uniquement fonctionnelle pour la version ordinateur.


Cette présentation se scinde en plusieurs parties :

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
On trie les liens, en effet ceux commençant par https://boutique. sont des articles publicitaires, donc pas intéressant à scraper.

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
sujet probable :  ('faitsDivers', 34.61538461538461)
Catégorie culture: 0.00 %
Catégorie economie: 19.23 %
Catégorie divers: 0.00 %
Catégorie ville: 26.92 %
Catégorie sport: 11.54 %
Catégorie faitsDivers: 34.62 %
Catégorie meteo: 3.85 %
Catégorie lieu: 3.85 %
L'article avec l'URL https://leveil.fr/puy-en-velay-43000/actualites/la-voiture-veut-tourner-et-percute-une-moto-les-faits-divers-en-haute-loire_14480930/ est déjà présent dans la base de données. Pas d'insertion.
Fichier téléversé avec succès sur le serveur FTP.
URL de l'image téléversée: /articles-data/img/leveil/eb33a61fafdf73fd5c6af98111222c1e03dd4eb1f5a8c25a375be73f5e3e46ed.webp
```

Le "sujet probable" me permet de déterminer la dominante de l'article pour pouvoir le classer dans une catégorie spéciale de mon site.

En suivant le lien de l'article, on peut vérifier qu'il s'agit bien d'un article sur un fait divers (accident), ce que confirme mon algorithme : "sujet probable :  ('faitsDivers', 34.61538461538461)" car la majorité des mots de cet article proviennent du vocabulaire du fait divers.

Notons qu'en traitant l'image (suppression de bordures, compression), je la convertis également en image.**webp**. En effet, ce type d'image est désormais plus adapté pour le web et pour le chargement des images. De plus ce genre d'extention permet de favoriser le SEO de Google.

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

## Partie 2, SQL, PHP :

1. Commençons par la partie sur le SQL :

L'entrée d'un article extrait dans la base de donnée passe par une requête python qui envoie les différentes données de l'article selon les colonnes : 

L'insertion passe par une simple fonction try, except, finally :

```python
def insert_article(title, description, journal, url, type, date_published, heure, image_s_link, keywords, trend_score):
    try:
        mydb = mysql.connector.connect(
            host="193.203.168.53",
            user="u508202719_marc",
            passwd= "Eh non, vous ne pourrez pas hacker ma base de donnée ☺",
            database="u508202719_actu"
        )

        mycursor = mydb.cursor()

        mycursor.execute(f"SELECT COUNT(*) FROM {journal} WHERE url = %s", (url,))
        count = mycursor.fetchone()[0]

        if count == 0:
            sql = f"INSERT INTO {journal} (title, description, journal, url, type, date_published, heure_published, image_s_link, keywords_article, category, trending_score) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            val = (
                title,
                description,
                journal,
                url,
                type,
                date_published,
                heure,
                image_s_link,
                json.dumps(keywords[0]),
                keywords[1][0],
                trend_score
            )
            mycursor.execute(sql, val)
            mydb.commit()
            print(f"Article inséré avec succès dans la base de données. ID: {mycursor.lastrowid}")
        else:
            print(f"L'article avec l'URL {url} est déjà présent dans la base de données. Pas d'insertion.")

    except mysql.connector.Error as err:
        print("Une erreur s'est produite lors de l'insertion de l'article :", err)

    finally:
        if mycursor:
            mycursor.close()
        if mydb:
            mydb.close()
```
EXPLICATION : avec le module mysql connector, on démarre une connexion à la db avec les identifiants, on sélectionne la table, et si la table existe on insert les données en écrivant la requête sql, on retrouve bien le langage sql avec INSERT INTO. Et après on met un petit message de réussite et on referme la connexion.

Voici une requete SQL type pour créer une table pour y stocker les articles du Progrès : 
On met simplement les éléments dont on a besoin, et on spécifie le type, donc pour la description on prend un varchar 255, pour la date on prend DATE et pour le trending score on prend INT car il s'agit d'une valeure chiffrée (+1 à chaque clics).

```sql
CREATE TABLE IF NOT EXISTS actu_leprogres (
    ID INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    journal VARCHAR(255),
    url VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    date_published DATE,
    heure_published TIME,  
    image_s_link VARCHAR(255),
    keywords_article VARCHAR(255),
    category VARCHAR(255),
    trending_score INT NOT NULL
);
```
2. Partie 2, Utilisation de php et mySQL :
Module de recherche du site : 

Lorsqu'une recherche est lancée, avec un <form> utilisant GET, on vient chercher le fichier actualite.php qui charge une nouvelle page avec les résultats de la reherche qui a été mise dans le form :
exemple de requête : https://gofeed.fr/actualite.php?recherche=informatique On voit bien que dans actualite.php?recherche={recherche} 'recherche' est le paramètre.

```php
<?php
$page = "recherche";
$recherche = $_GET['recherche'];
?>
```

Et ensuite dans un fichier php, on effectue une requête SQL pour afficher au maximum 100 résultats suite à la recherche : 

On recherche parmi les tables (peut être amélioré en effctuant une boucle), comme vous le voyez on recherche parmi la description, le titre etc. Et on ordonne tous ces résultats par DATE (du plus récents au plus ancien) et par tendance.
```php
$sql = "SELECT 
    *
FROM (
    SELECT 
        *
    FROM 
        actu_actufr
    WHERE 
        title LIKE '%$recherche%'
        OR description LIKE '%$recherche%'
        OR journal LIKE '%$recherche%'
        OR url LIKE '%$recherche%'
        OR type LIKE '%$recherche%'
        OR date_published LIKE '%$recherche%'
        OR keywords_article LIKE '%$recherche%'
    UNION
    SELECT 
        *
    FROM 
        actu_dauphinelibere
    WHERE 
        title LIKE '%$recherche%'
        OR description LIKE '%$recherche%'
        OR journal LIKE '%$recherche%'
        OR url LIKE '%$recherche%'
        OR type LIKE '%$recherche%'
        OR date_published LIKE '%$recherche%'
        OR keywords_article LIKE '%$recherche%'
    UNION
    SELECT 
        *
    FROM 
        actu_france3region
    WHERE 
        title LIKE '%$recherche%'
        OR description LIKE '%$recherche%'
        OR journal LIKE '%$recherche%'
        OR url LIKE '%$recherche%'
        OR type LIKE '%$recherche%'
        OR date_published LIKE '%$recherche%'
        OR keywords_article LIKE '%$recherche%'
    UNION
    SELECT 
        *
    FROM 
        actu_lacommere43
    WHERE 
        title LIKE '%$recherche%'
        OR description LIKE '%$recherche%'
        OR journal LIKE '%$recherche%'
        OR url LIKE '%$recherche%'
        OR type LIKE '%$recherche%'
        OR date_published LIKE '%$recherche%'
        OR keywords_article LIKE '%$recherche%'
    UNION
    SELECT 
        *
    FROM 
        actu_lamontagne
    WHERE 
        title LIKE '%$recherche%'
        OR description LIKE '%$recherche%'
        OR journal LIKE '%$recherche%'
        OR url LIKE '%$recherche%'
        OR type LIKE '%$recherche%'
        OR date_published LIKE '%$recherche%'
        OR keywords_article LIKE '%$recherche%'
    UNION
    SELECT 
        *
    FROM 
        actu_leprogres
    WHERE 
        title LIKE '%$recherche%'
        OR description LIKE '%$recherche%'
        OR journal LIKE '%$recherche%'
        OR url LIKE '%$recherche%'
        OR type LIKE '%$recherche%'
        OR date_published LIKE '%$recherche%'
        OR keywords_article LIKE '%$recherche%'
    UNION
    SELECT 
        *
    FROM 
        actu_leveil
    WHERE 
        title LIKE '%$recherche%'
        OR description LIKE '%$recherche%'
        OR journal LIKE '%$recherche%'
        OR url LIKE '%$recherche%'
        OR type LIKE '%$recherche%'
        OR date_published LIKE '%$recherche%'
        OR keywords_article LIKE '%$recherche%'
    UNION
    SELECT 
        *
    FROM 
        actu_zoomdici
    WHERE 
        title LIKE '%$recherche%'
        OR description LIKE '%$recherche%'
        OR journal LIKE '%$recherche%'
        OR url LIKE '%$recherche%'
        OR type LIKE '%$recherche%'
        OR date_published LIKE '%$recherche%'
        OR keywords_article LIKE '%$recherche%'
) AS all_tables
ORDER BY 
    date_published DESC, 
    trending_score DESC LIMIT 100;



";
```

Page d'accueil de gofeed.fr, classement des articles par tendance et par date :

Sur la page d'accueil du site, je classe les articles par tendance (trending_score) : nombre de clics sur l'articles, et par date (date de la plus récente à la plus ancienne).

J'utilise UNION ALL pour disposer les articles par "category", et donc j'utilise LIMIT pour avoir seulement qu'une quantité précise d'article retournés par mySQL :
```sql
$sql = "(
    SELECT * FROM (
        SELECT *,
            LAG(source_table) OVER (ORDER BY date_published DESC, trending_score DESC) AS prev_table
        FROM (
            SELECT *, 'actu_actufr' AS source_table FROM actu_actufr
            UNION ALL
            SELECT *, 'actu_dauphinelibere' AS source_table FROM actu_dauphinelibere
            UNION ALL
            SELECT *, 'actu_france3region' AS source_table FROM actu_france3region
            UNION ALL
            SELECT *, 'actu_lacommere43' AS source_table FROM actu_lacommere43
            UNION ALL
            SELECT *, 'actu_lamontagne' AS source_table FROM actu_lamontagne
            UNION ALL
            SELECT *, 'actu_leprogres' AS source_table FROM actu_leprogres
            UNION ALL
            SELECT *, 'actu_leveil' AS source_table FROM actu_leveil
            UNION ALL
            SELECT *, 'actu_zoomdici' AS source_table FROM actu_zoomdici
        ) AS combined
    ) AS with_prev_table
    WHERE prev_table IS NULL OR prev_table != source_table
    ORDER BY date_published DESC, trending_score DESC
    LIMIT 5
)

UNION ALL

(
    -- mot-clé 'economie'
    SELECT * FROM (
        SELECT *,
            LAG(source_table) OVER (ORDER BY date_published DESC, trending_score DESC) AS prev_table
        FROM (
            SELECT *, 'actu_actufr' AS source_table FROM actu_actufr
            UNION ALL
            SELECT *, 'actu_dauphinelibere' AS source_table FROM actu_dauphinelibere
            UNION ALL
            SELECT *, 'actu_france3region' AS source_table FROM actu_france3region
            UNION ALL
            SELECT *, 'actu_lacommere43' AS source_table FROM actu_lacommere43
            UNION ALL
            SELECT *, 'actu_lamontagne' AS source_table FROM actu_lamontagne
            UNION ALL
            SELECT *, 'actu_leprogres' AS source_table FROM actu_leprogres
            UNION ALL
            SELECT *, 'actu_leveil' AS source_table FROM actu_leveil
            UNION ALL
            SELECT *, 'actu_zoomdici' AS source_table FROM actu_zoomdici
        ) AS combined
    ) AS with_prev_table
    WHERE (prev_table IS NULL OR prev_table != source_table)
    AND category = 'economie'
    ORDER BY date_published DESC, trending_score DESC
    LIMIT 4 OFFSET 5
)

UNION ALL
etc
```

AND category = 'economie' pour récupérer uniquement des mot de cette catégorie.

AS with_prev_table
    WHERE (prev_table IS NULL OR prev_table != source_table) sert à ne pas remettre des articles déjà sortis dans les requêtes précédentes.


Évaluation du score tendance d'un article : 

Pour évaluer le score tendance d'un article, j'ai mis en place un petit script javascript qui comporte une fonction asynchrone : dès qu'un article est cliqué, on incrémente la colonne trending score de l'article. J'utilise fetch avec la methode POST. 

En HTML, chaque balise <article> comprend un onclick() avec comme argument de data-id de l'article pour cibler le numéro de l'article et le data-journal pour trouver la table :  incrementTrend(&quot;actu_dauphinelibere&quot;, &quot;1000047&quot;);"
```html

<article class="margin-top-10 width-12 bbrr bblr" data-journal="actu_dauphinelibere" data-id="1000047" data-link="aHR0cHM6Ly93d3cubGVkYXVwaGluZS5jb20vZWNvbm9taWUvMjAyNC8wNC8wMi9tZW1lLXNpLXRvdXQtbi1lc3QtcGFzLXBhcmZhaXQtcGVyc29ubmUtbi1lc3Qtb3VibGllLWxhLXByZWZlY3R1cmUtcHJvbWV0LXVuLWRlbWktbWlsbGlhcmQtZC1ldXJvcy1wb3VyLWxhLXJ1cmFsaXRl%7CS2VrcmFr" onclick="linkRedirection(this.getAttribute(&quot;data-link&quot;)); incrementTrend(&quot;actu_dauphinelibere&quot;, &quot;1000047&quot;);">
```

Je vous propose de voir par vous même, quand vous cliquer sur un article, un console log dans la console javascript affiche incrémentation réussie. Si vous cliquez une dizaine de fois sur l'article, vous verrez qu'au chargement de la page cet article monte, jusqu'à venir en tête du site.
Si vous ne voulez pas vous fatiguer à spammer un article, je vous propose simplement de recopier ce code :

Il suffit d'aller sur le site, prendre un article de second plan, qui date d'aujourd'hui, d'aller dans l'inspecteur, trouver le data-journal et le data-id, les mettre dans : incrementTrend(//// METTRE NOM JOURNAL DATA-JOURNAL//////// en type str, ///////METTRE DATA-ID CORRESPONDANT en type str////////) 

J'ai mis une itération de 40 pour simuler 40 clics, dès lors, au rechargement de la page vous verrez que l'article sera au premier plan. (il est facile de manipuler la position des articles étant donné le fait que j'ai très peu d'utilisateurs)

```javascript

async function incrementTrend(journal, id) {
    const url = '_increment_trend_system_.php';

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `id=${id}&table=${journal}`,
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const data = await response.text(); 
        if (data === 'OK') {
            console.log('Incrémentation réussie !');
        } else {
            console.error('Erreur lors de l\'incrémentation :', data);
        }
    } catch (error) {
        console.error('Erreur système : Incrémentation :', error.message);
    }
}

for (let i = 0; i < 40; i++) {
incrementTrend(//// METTRE NOM JOURNAL DATA-JOURNAL//////// en type str, ///////METTRE DATA-ID CORRESPONDANT en type str////////)
}


```
EXEMPLE : 
```

for (let i = 0; i < 40; i++) {
incrementTrend("actu_leprogres", "5000774")

```

Et vous verrez que l'article s'affichera tout en haut.

Un peu de CSS :

Vous pouvez remarquer qu'il y a souvent des classes css commune, c'est parce que je préfère appliquer un style aux éléments directement, sans passer par des noms complexes. 
Exemple : Je trouve bien plus pratique d'écrire : 
```
<article class="margin-top-10 width-12 bbrr bblr"
```

On comprend directement que chaque article a margin-top: 10px, une wisth de 12rem, et bbrr bblr pour les bord, donc logiquement : border-bottom-right-radius et bb-left-radius.
Ainsi j'ai un document css qui regroupe nombre de caractérisations communes (ci joint) comme display-flex-all :
display:flex; justify-content:center; align-items:center;
flex-wrap-wrap : display:flex; flex-wrap: wrap 

etc



Je n'ai pas complètement fini la présentation mais si vous avez des questions je suis entièrment disponible. 
marc.mathieu43@gmail.com
07 82 09 84 76
