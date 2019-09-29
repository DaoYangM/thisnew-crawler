import datetime

import re
import json

import requests

from database import CrawlerDB
from error import RequestError, ReviewListError
from tools import review_resolver, Review, get_logging, CrawlerType, request_resolver

# vistal每次最多获取25条评论
PAGE_SIZE = 25

# vista获取producttype, zidProductID 正则
VISTA_REGEX = r'"page_id":"(.*?)","api_key":"(.*?)","locale":"(.*?)",".*?","merchant_id":"(.*?)",'

# vista评论api地址 https://display.powerreviews.com/m/685351/l/en_US/product/MP-206605/reviews
VISTA_REVIEW_API = 'https://display.powerreviews.com/m/'

# 请求头部, 如果没有设置Vista拒绝访问
HEADER = {
    'Origin': 'https://www.vistaprint.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/76.0.3809.100 Safari/537.36',
    'Sec-Fetch-Mode': 'cors',
    'Referer': 'https://www.vistaprint.com'
}

# 获得日志对象
logging = get_logging()


class VistaProduct:
    """通过Vista商品url获得评论api请求参数"""

    def __init__(self, product_url):
        """
        init
        Args:
            product_url: Vista商品url
        """

        self.product_url = product_url
        self.__params = {
            'GP': '09/29/2019 05:19:49',
            'GPS': '5489783259',
            'GNF': '0',
        }

    def get_review_api_params(self):
        """
        通过product_url 获得product_type 和 root_product_id
        这些都是Vista review api 所必要的参数
        Returns:
            product_type: zazzle商品类型
            root_product_id: zazzle根商品id
        """

        # 第一次请求获得response返回的cookies
        response = request_resolver(url=self.product_url, params=None, header=HEADER)
        cookies = requests.utils.dict_from_cookiejar(response.cookies)

        # 第二次请求带上第一请求返回的cookies, 如果没有cookies, vista要求加载js
        response = request_resolver(url=self.product_url, params=None, header=HEADER, cookies=cookies)

        pattern = re.compile(VISTA_REGEX)
        match = re.search(pattern, response.text)

        if match:
            return match.group(1), match.group(2), match.group(3), match.group(4)
        else:
            logging.error(
                'Getting product error product url: ' + self.product_url,
                exc_info=True
            )


class VistaReview:
    """获取vista评论"""

    def __init__(self, vista_product_id, merchant_id, api_key, locale):
        """
        init
        Args:
            vista_product_id: vistal商品id
            merchant_id: merchant_id
            api_key: apikey
            locale: 区域
        """

        self.__vista_product_id = vista_product_id
        self.__merchant_id = merchant_id
        self.__api_key = api_key
        self.__locale = locale

    def get_reviews(self, rating, review_counts):
        """
        获取根据review_counts和PAGE_SIZE按照rating进行分页请求
        Args:
            rating: 请求评论星级
            review_counts: 所需评论总数
        Returns:
            所获的评论
        """

        results = list()

        if review_counts != -1:
            loop_times = review_counts // PAGE_SIZE
            remainder = review_counts % PAGE_SIZE
            time = 0

            for _ in range(loop_times):
                results.extend(self.__get_reviews(time, PAGE_SIZE, rating))
                time += PAGE_SIZE
            if remainder > 0:
                results.extend(self.__get_reviews(time, remainder, rating))
        else:
            results.extend(self.__get_reviews(0, PAGE_SIZE, rating))

        return results

    def __get_reviews(self, page_num, page_size, rating):
        """
        真正请求的评论的接口
        Args:
            page_num: 页数
            page_size: 次页的条数
            rating: 需要的评分
        Returns:
            次页所获得的评论
        """

        params = {
            'paging.from': page_num,
            'paging.size': page_size,
            'image_only': False,
            'apikey': self.__api_key,
            'sort': 'HighestRating',
        }

        if rating != -1:
            params['filters'] = 'rating:' + str(rating)

        review_api = VISTA_REVIEW_API + self.__merchant_id + '/l/' + self.__locale + '/product/' + self.__vista_product_id + '/reviews'

        response = request_resolver(review_api, params=params, header=HEADER)

        json_content = json.loads(response.text)

        if response.ok:
            review_list = list()
            if json_content['results'] and json_content['results'][0]:
                reviews = json_content['results'][0]['reviews']

                for review in reviews:
                    text = review_resolver(review['details']['comments'], CrawlerType.VISTA)
                    rating = rating
                    date_add = datetime.datetime.fromtimestamp(review['details']['created_date'] / 1000).strftime("%Y-%m-%d %H:%M:%S")
                    author = review['details']['nickname'] if review['details']['nickname'] else 'anonymous'
                    review_list.append(Review(text=text, rating=rating, date_add=date_add, author=author))

                logging.info("  rating: " + str(rating) +
                             "  page_num: " + str(page_num) + ", review_list: " + str(len(review_list)))
            return review_list

        else:
            logging.error(
                'Getting reviews error vista_product_id: ' + self.__vista_product_id + ' merchant_id: ' + self.__merchant_id
                + ' api_key: ' + self.__api_key + ' locale: ' + self.__locale + ' page_num: ' + str(page_num) + ' page_size:' + str(page_size),
                exc_info=True
            )
            raise


class ZazzleReviewCrawler:
    def __init__(self, product_url, review_counts, task_id, ratings, this_new_product_ids):
        """
        init
        Args:
            product_url: 商品url
            review_counts: 总共需要多少评论
            task_id: oc_review_catch_task 主键
            ratings: 评分星级list [5, 4 ,3, 2, 1]
            this_new_product_ids: thisnew的商品id list
        """
        self.__product_url = product_url
        self.__review_counts = review_counts
        self.__task_id = task_id
        self.__ratings = ratings
        self.__ratings.sort(reverse=True)
        self.__this_new_product_ids = this_new_product_ids

    def get_reviews(self):
        """调度方法"""

        product = VistaProduct(self.__product_url)
        try:
            vistal_product_id, api_key, locale, merchant_id = product.get_review_api_params()
            logging.info(
                '[VISTA] vistal_product_id: ' + vistal_product_id + ', api_key: ' + api_key + ', locale' + locale + ', merchant_id' + merchant_id + ', ratings: ' + str(
                    self.__ratings) + ", review_count: " + str(self.__review_counts))

            vista_list = list()

            for rating in self.__ratings:
                if len(vista_list) < self.__review_counts:
                    vista_review = VistaReview(vista_product_id=vistal_product_id, merchant_id=merchant_id, api_key=api_key, locale=locale)
                    vista_list.extend(
                        vista_review.get_reviews(rating=rating,
                                                 review_counts=self.__review_counts - len(vista_list)))

            logging.info(len(vista_list))
            if len(vista_list) > len(self.__this_new_product_ids):
                CrawlerDB.insert_reviews(review_list=vista_list, thisnew_product_ids=self.__this_new_product_ids)
                CrawlerDB.update_crawler_status_success(self.__task_id)
            else:
                raise ReviewListError("review list less than thisnew product ids")

        except (RequestError, ReviewListError):
            CrawlerDB.update_crawler_status_fail(self.__task_id)


if __name__ == '__main__':
    ZazzleReviewCrawler(
        product_url='https://www.vistaprint.com/signs-posters/foam-board-signs',
        review_counts=11, task_id=1, ratings=[5, 4, 3, 2, 1], this_new_product_ids=[110, 54]).get_reviews()
