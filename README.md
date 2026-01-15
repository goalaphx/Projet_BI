
# Projet_BI

## Data Collection

### Prérequis

Assurez-vous d’avoir **Python**, **pip** et **Docker** installés sur votre machine.

### Installation des dépendances

```bash
pip install scrapy scrapy-splash pymongo
````

### Lancement de Splash (rendu JavaScript)

```bash
docker run -p 8050:8050 scrapinghub/splash
```

### Lancement de MongoDB

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### Services utilisés

* **Scrapy** : Framework de web scraping
* **Splash** : Rendu des pages JavaScript
* **MongoDB** : Stockage des données collectées

