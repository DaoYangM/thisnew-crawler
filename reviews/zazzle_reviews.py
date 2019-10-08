# coding=utf-8

import datetime

import re
import json

from reviews.config import ZAZZLE_REGEX, ZAZZLE_PAGE_SIZE, ZAZZLE_REVIEW_API, ZAZZLE_HEADER
from reviews.tools import review_resolver, Review, get_logging, CrawlerType, request_resolver

# 获得日志对象
logging = get_logging()


class ZazzleProduct:
    """通过zazzle商品url获得评论api请求参数"""

    def __init__(self, product_url):
        """
        init
        Args:
            product_url: zazzle商品url
        """

        self.product_url = product_url

    def get_review_api_params(self):
        """
        通过product_url 获得product_type 和 root_product_id
        这些都是zazzle review api 所必要的参数
        Returns:
            product_type: zazzle商品类型
            root_product_id: zazzle根商品id
        """

        response = request_resolver(url=self.product_url, header=ZAZZLE_HEADER)

        pattern = re.compile(ZAZZLE_REGEX)
        match = re.search(pattern, response.text)
        if match:
            product_type = match.group(1)
            product_id = match.group(2)
            logging.info(
                '{ZAZZLE API PARAMS} -> [product_type]: ' + product_type + ', [root_product_id]: ' + product_id)
            return ZazzleReviewApiParams(product_type, product_id)
        else:
            logging.error(
                'Getting product error product url: ' + self.product_url,
                exc_info=True
            )


class ZazzleReviewApiParams:
    def __init__(self, zazzle_product_type, root_product_id):
        """
        init
        Args:
            zazzle_product_type: zazzle商品类型
            root_product_id: zazzle根商品id
        """

        self.__product_type = zazzle_product_type
        self.__root_product_id = root_product_id

    def get_params(self):
        return self.__product_type, self.__root_product_id


class ZazzleReview:
    """
    获取zazzle评论
    """

    def __init__(self, zazzle_review_api_params):
        """
        init
        Args:
            zazzle_review_api_params: zazzle 评论api所需参数 ZazzleReviewApiParams
        """
        zazzle_product_type, root_product_id = zazzle_review_api_params.get_params()
        self.__product_type = zazzle_product_type
        self.__root_product_id = root_product_id

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
            loop_times = review_counts // ZAZZLE_PAGE_SIZE
            remainder = review_counts % ZAZZLE_PAGE_SIZE

            for time in range(loop_times):
                results.extend(self.__get_reviews(time + 1, ZAZZLE_PAGE_SIZE, rating))
            if remainder > 0:
                results.extend(self.__get_reviews(loop_times + 1, remainder, rating))
        else:
            results.extend(self.__get_reviews(1, ZAZZLE_PAGE_SIZE, rating))

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
            'cv': 1,
            'cacheDefeat': 1569293331342,
            'pageNum': page_num,
            'pageSize': page_size,
            'productType': self.__product_type,
            'rootProductId': self.__root_product_id,
            'sortBy': 'RatingDesc',
            'client': 'js'
        }

        if rating != -1:
            params['rating'] = rating

        response = request_resolver(ZAZZLE_REVIEW_API, params=params, header=ZAZZLE_HEADER)

        json_content = json.loads(response.text)

        if response.ok and json_content['success']:
            review_list = list()
            if json_content['data']['entities']:
                reviews = json_content['data']['entities']['reviews']
                user_profiles = json_content['data']['entities']['profiles']

                for review in reviews.values():
                    text = review_resolver(review['optionReview'], CrawlerType.ZAZZLE)
                    rating = rating
                    try:
                        date_add = datetime.datetime.strptime(review['dateCreated'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    except ValueError:
                        date_add = datetime.datetime.strptime(review['dateCreated'], "%Y-%m-%dT%H:%M:%SZ")
                    author = user_profiles[review['reviewerId']]['name'] if user_profiles[review['reviewerId']][
                        'name'] else 'anonymous'
                    review_list.append(Review(text=text, rating=rating, date_add=date_add, author=author))

                logging.info("  rating: " + str(rating) +
                             "  page_num: " + str(page_num) + ", review_list: " + str(len(review_list)))
            return review_list

        else:
            logging.error(
                'Getting reviews error product_type: ' + self.__product_type + ' root_product_id: ' + self.__root_product_id
                + ' page_num: ' + str(page_num) + ' page_size:' + str(page_size),
                exc_info=True
            )
            raise
