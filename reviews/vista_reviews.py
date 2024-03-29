# coding=utf-8

import datetime

import re
import json

import requests

from reviews.config import VISTA_REGEX, VISTA_PAGE_SIZE, VISTA_REVIEW_API, VISTA_HEADER
from reviews.error import RequestParamError
from reviews.tools import review_resolver, Review, get_logging, CrawlerType, request_resolver

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
        response = request_resolver(url=self.product_url, params=None, header=VISTA_HEADER)
        cookies = requests.utils.dict_from_cookiejar(response.cookies)

        # 第二次请求带上第一请求返回的cookies, 如果没有cookies, vista要求加载js
        response = request_resolver(url=self.product_url, params=None, header=VISTA_HEADER, cookies=cookies)

        pattern = re.compile(VISTA_REGEX)
        match = re.search(pattern, response.text)

        if match:
            vista_product_id = match.group(1)
            api_key = match.group(2)
            locale = match.group(3)
            merchant_id = match.group(4)

            logging.info(
                '{VISTA API PARAMS} -> [vista_product_id]: ' + vista_product_id + ', [api_key]: ' + api_key + ', [locale]: ' + locale + ', [merchant_id]: ' + merchant_id)

            return VistaReviewApiParams(vista_product_id, api_key, locale, merchant_id)
        else:
            msg = '[Getting API PARAM] error product url: ' + self.product_url
            logging.error(msg)
            raise RequestParamError(msg)


class VistaReviewApiParams:
    def __init__(self, vista_product_id, api_key, locale, merchant_id):
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

    def get_params(self):
        return self.__vista_product_id, self.__merchant_id, self.__api_key, self.__locale


class VistaReview:
    """获取vista评论"""

    def __init__(self, zazzle_review_api_params):
        """
        init
        Args:
            zazzle_review_api_params: vistal商品id
        """

        vista_product_id, merchant_id, api_key, locale = zazzle_review_api_params.get_params()

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
            loop_times = review_counts // VISTA_PAGE_SIZE
            remainder = review_counts % VISTA_PAGE_SIZE
            time = 0
            is_done = False
            for _ in range(loop_times):
                reviews = self.__get_reviews(time, VISTA_PAGE_SIZE, rating)
                if len(reviews) < 1:
                    is_done = True
                    break
                results.extend(reviews)
                time += VISTA_PAGE_SIZE
            if not is_done and remainder > 0:
                results.extend(self.__get_reviews(time, remainder, rating))
        else:
            results.extend(self.__get_reviews(0, VISTA_PAGE_SIZE, rating))

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

        response = request_resolver(review_api, params=params, header=VISTA_HEADER)

        json_content = json.loads(response.text)

        if response.ok:
            review_list = list()
            if json_content['results'] and json_content['results'][0]:
                reviews = json_content['results'][0]['reviews']

                for review in reviews:
                    text = review_resolver(review['details']['comments'], CrawlerType.VISTA)
                    rating = rating
                    date_add = datetime.datetime.fromtimestamp(review['details']['created_date'] / 1000).strftime(
                        "%Y-%m-%d %H:%M:%S")
                    author = review['details']['nickname'] if review['details']['nickname'] else 'anonymous'
                    review_list.append(Review(text=text, rating=rating, date_add=date_add, author=author))

                if len(review_list) > 0:
                    logging.info("  rating: " + str(rating) +
                                 "  page_num: " + str(page_num) + ", review_list: " + str(len(review_list)))
            return review_list

        else:
            logging.error(
                '[Getting REVIEWS] error vista_product_id: ' + self.__vista_product_id + ' merchant_id: ' + self.__merchant_id
                + ' api_key: ' + self.__api_key + ' locale: ' + self.__locale + ' page_num: ' + str(
                    page_num) + ' page_size:' + str(page_size),
                exc_info=True
            )
            raise requests.exceptions.RequestException(response)
