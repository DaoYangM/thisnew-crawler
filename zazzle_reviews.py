import datetime

import re
import json

from database import CrawlerDB
from error import RequestError, ReviewListError
from tools import review_resolver, Review, get_logging, CrawlerType, request_resolver

# zazzle每次最多获取100条评论
PAGE_SIZE = 100

# zazzle获取producttype, zidProductID 正则
ZAZZLE_REGEX = '"producttype":"(.*?)","zidProductID":"(.*?)"'

# zazzle评论api地址s
ZAZZLE_REVIEW_API = 'https://www.zazzle.com/svc/z3/reviews/get'

# 请求头部, 如果没有设置zazzle拒绝访问
HEADER = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/76.0.3809.100 Safari/537.36',
    'Sec-Fetch-Mode': 'cors',
    'Referer': 'https://www.zazzle.com/'
}

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

    def get_product_type_and_root_product_id(self):
        """
        通过product_url 获得product_type 和 root_product_id
        这些都是zazzle review api 所必要的参数
        Returns:
            product_type: zazzle商品类型
            root_product_id: zazzle根商品id
        """

        response = request_resolver(url=self.product_url, header=HEADER)

        pattern = re.compile(ZAZZLE_REGEX)
        match = re.search(pattern, response.text)
        if match:
            return match.group(1), match.group(2)
        else:
            logging.error(
                'Getting product error product url: ' + self.product_url,
                exc_info=True
            )


class ZazzleReview:
    """
    获取zazzle评论
    """

    def __init__(self, zazzle_product_type, root_product_id):
        """
        init
        Args:
            zazzle_product_type: zazzle商品类型
            root_product_id: zazzle根商品id
        """

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
            loop_times = review_counts // PAGE_SIZE
            remainder = review_counts % PAGE_SIZE

            for time in range(loop_times):
                results.extend(self.__get_reviews(time + 1, PAGE_SIZE, rating))
            if remainder > 0:
                results.extend(self.__get_reviews(loop_times + 1, remainder, rating))
        else:
            results.extend(self.__get_reviews(1, PAGE_SIZE, rating))

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

        response = request_resolver(ZAZZLE_REVIEW_API, params=params, header=HEADER)

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

        product = ZazzleProduct(self.__product_url)
        try:
            product_type, product_id = product.get_product_type_and_root_product_id()
            logging.info(
                '[ZAZZLE] product_type: ' + product_type + ', root_product_id: ' + product_id + ', ratings: ' + str(
                    self.__ratings) + ", review_count: " + str(self.__review_counts))

            review_list = list()

            for rating in self.__ratings:
                if len(review_list) < self.__review_counts:
                    zazzle_review = ZazzleReview(product_type, product_id)
                    review_list.extend(
                        zazzle_review.get_reviews(rating=rating,
                                                  review_counts=self.__review_counts - len(review_list)))

            logging.info(len(review_list))
            if len(review_list) > len(self.__this_new_product_ids):
                CrawlerDB.insert_reviews(review_list=review_list, thisnew_product_ids=self.__this_new_product_ids)
                CrawlerDB.update_crawler_status_success(self.__task_id)
            else:
                raise ReviewListError("review list less than thisnew product ids")

        except (RequestError, ReviewListError):
            CrawlerDB.update_crawler_status_fail(self.__task_id)


if __name__ == '__main__':
    ZazzleReviewCrawler(
        product_url='https://www.zazzle.com/pd/spp/pt-mojo_throwpillow?fabric=poly&style=16x16',
        review_counts=230, task_id=1, ratings=[5, 4, 3, 2, 1], this_new_product_ids=[110, 54]).get_reviews()
