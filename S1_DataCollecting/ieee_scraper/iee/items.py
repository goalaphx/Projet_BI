import scrapy

class IeeItem(scrapy.Item):
    title = scrapy.Field()
    authors = scrapy.Field()
    date_pub = scrapy.Field()
    source = scrapy.Field()      # Critical: Added this to support "IEEE" tag
    journal = scrapy.Field()
    abstract_ = scrapy.Field()   # Added for abstract text (defaulting to "N/A")
    topic = scrapy.Field()
    country = scrapy.Field()     
    latitude = scrapy.Field()
    longitude = scrapy.Field()