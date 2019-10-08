# coding=utf-8

HOST = '10.101.10.203'
PORT = 3306
USERNAME = 'thisnew'
PASSWORD = 'thisnew2019'
DB = 'ThisNew_EMERGENCY'
CHARSET = 'utf8mb4'

# redis地址
REDIS_ADDR = 'www.daoyang.design'
REDIS_PORT = '6379'
# redis 爬虫键值
REDIS_CRAWLER_KEY = 'CRAWLER_REVIEWS'

# 爬虫customer_id, 用于填写在插入oc_review表的customer_id字段
CRAWLER_ID = 53

# 日志文件目录
LOG_PATH = './logs/'

# 日志文件名
LOG_FILENAME = LOG_PATH + 'thisnew_crawlers.log'

# zazzle每次最多获取100条评论
ZAZZLE_PAGE_SIZE = 100

# zazzle获取producttype, zidProductID 正则
ZAZZLE_REGEX = '"producttype":"(.*?)","zidProductID":"(.*?)"'

# zazzle评论api地址s
ZAZZLE_REVIEW_API = 'https://www.zazzle.com/svc/z3/reviews/get'

# 请求头部, 如果没有设置zazzle拒绝访问
ZAZZLE_HEADER = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/76.0.3809.100 Safari/537.36',
    'Sec-Fetch-Mode': 'cors',
    'Referer': 'https://www.zazzle.com/'
}

# vista获取producttype, zidProductID 正则
VISTA_REGEX = r'"page_id":"(.*?)","api_key":"(.*?)","locale":"(.*?)",".*?","merchant_id":"(.*?)",'

# vista每次最多获取25条评论
VISTA_PAGE_SIZE = 25

# vista评论api地址 https://display.powerreviews.com/m/685351/l/en_US/product/MP-206605/reviews
VISTA_REVIEW_API = 'https://display.powerreviews.com/m/'

# 请求头部, 如果没有设置Vista拒绝访问
VISTA_HEADER = {
    'Origin': 'https://www.vistaprint.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/76.0.3809.100 Safari/537.36',
    'Sec-Fetch-Mode': 'cors',
    'Referer': 'https://www.vistaprint.com'
}
