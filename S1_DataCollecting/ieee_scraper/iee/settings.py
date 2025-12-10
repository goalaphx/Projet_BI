BOT_NAME = 'iee'

SPIDER_MODULES = ['iee.spiders']
NEWSPIDER_MODULE = 'iee.spiders'

# Ignore robots.txt to ensure we can scrape freely
ROBOTSTXT_OBEY = False

# --- MONGODB SETUP ---
# Enable the pipeline we defined above
ITEM_PIPELINES = {
   'iee.pipelines.MongoPipeline': 300,
}

# Database Connection Details
MONGODB_SERVER = "localhost"
MONGODB_PORT = 27017
MONGODB_DB = "aci"
MONGODB_COLLECTION = "articles"

# (Optional) Disable default User-Agent if you want, 
# but Selenium sets its own User-Agent inside the spider anyway.