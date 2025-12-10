# sciencedirect_scraper/settings.py
BOT_NAME = 'sciencedirect'
SPIDER_MODULES = ['sciencedirect.spiders']
NEWSPIDER_MODULE = 'sciencedirect.spiders'
ROBOTSTXT_OBEY = False

# MongoDB Pipeline
ITEM_PIPELINES = {
   'sciencedirect.pipelines.MongoPipeline': 300,
}

# Database Settings
MONGODB_SERVER = "localhost"
MONGODB_PORT = 27017
MONGODB_DB = "aci"
MONGODB_COLLECTION = "articles"