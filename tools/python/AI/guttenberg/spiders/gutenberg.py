from os import write
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from guttenberg.items import GuttenbergItem

class GutenbergSpider(CrawlSpider):
    name = 'gutenberg'
    allowed_domains = ['www.gutenberg.org','aleph.gutenberg.or']
    search='Plato'
    start_urls = ['http://www.gutenberg.org/robot/harvest?filetypes[]=txt&langs[]=en']
    #['https://www.gutenberg.org/ebooks/search/?query='+ search +'&submit_search=Go!']
  #https://www.gutenberg.org/ebooks/search/?query=plato&submit_search=Go!
    rules = (
        Rule(LinkExtractor(), callback='parse_item', follow=False),
    )

    def parse_item(self, response):
        title_text = response.xpath('/html/body/h1').get()
        print('title')
        print(title_text)
        file_urls =[]
        for lank in response.xpath('/html/body/p'):
            this_url = lank.css('a::attr(href)').get()
            print(this_url)
            file_urls.insert(0,response.urljoin(this_url))
            #}# 
       # #write(response);
        item = GuttenbergItem()
        item['file_urls']=file_urls
        # link = response.xpath('/html/body/table/tbody/tr[23]/td[2]/span[2]/a').getall()
        # #item['name'] = response.xpath('//div[@id="name"]').get()
        # #item['description'] = response.xpath('//div[@id="description"]').get()
        # print(link)
        return item