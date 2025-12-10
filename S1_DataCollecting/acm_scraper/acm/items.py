import scrapy

class AcmItem(scrapy.Item):
    title = scrapy.Field()
    authors = scrapy.Field()
    date_pub = scrapy.Field()
    source = scrapy.Field()
    journal = scrapy.Field()
    abstract_ = scrapy.Field()