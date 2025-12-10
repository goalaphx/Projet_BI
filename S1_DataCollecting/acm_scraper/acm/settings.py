# acm_scraper/settings.py

BOT_NAME = 'acm'

SPIDER_MODULES = ['acm.spiders']
NEWSPIDER_MODULE = 'acm.spiders'

# Ignore robots.txt
ROBOTSTXT_OBEY = False

# --- MONGODB PIPELINE SETUP ---
ITEM_PIPELINES = {
   # FIX: Change 'acm_scraper' to 'acm' here!
   'acm.pipelines.MongoPipeline': 300,
}

# Database Settings
MONGODB_SERVER = "localhost"
MONGODB_PORT = 27017
MONGODB_DB = "aci"
MONGODB_COLLECTION = "articles"