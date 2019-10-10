# coding=utf-8
import json

import redis

from reviews.config import REDIS_ADDR, REDIS_PORT, REDIS_CRAWLER_KEY
from reviews.database import CrawlerDB
from reviews.error import RequestError, ReviewListError

# 获得日志对象
from reviews.tools import get_logging, CrawlerType
from reviews.vista_reviews import VistaProduct, VistaReview
from reviews.zazzle_reviews import ZazzleProduct, ZazzleReview

logging = get_logging()


class ReviewCrawler:
    def __init__(self, product_url, review_counts, task_id, crawler_type, ratings, this_new_product_ids):
        """
        init
        Args:
            product_url: 商品url
            review_counts: 总共需要多少评论
            task_id: oc_review_catch_task 主键
            crawler_type: 爬虫类型 CrawlerType
            ratings: 评分星级list [5, 4 ,3, 2, 1]
            this_new_product_ids: thisnew的商品id list
        """
        self.__product_url = product_url
        self.__review_counts = review_counts
        self.__task_id = task_id
        self.__crawler_type = crawler_type
        self.__ratings = ratings
        self.__ratings.sort(reverse=True)
        self.__this_new_product_ids = this_new_product_ids

    def get_reviews(self):
        """调度方法"""

        logging.info(' [crawler_type]: ' + str(
            self.__crawler_type) + ', [product_url]: ' + str(self.__product_url) + ', [review_counts]: ' + str(
            self.__review_counts)
                     + ', [task_id]: ' + str(self.__task_id) + ', [ratings]: '
                     + str(self.__ratings) + ', [this_new_product_ids]: ' + str(self.__this_new_product_ids))

        if self.__crawler_type == CrawlerType.ZAZZLE:
            self.__get_reviews(ZazzleProduct, ZazzleReview)

        elif self.__crawler_type == CrawlerType.VISTA:
            self.__get_reviews(VistaProduct, VistaReview)

    def __get_reviews(self, type_product_cls, type_review_cls):
        """
        真实调用方法
        Args:
            type_product_cls: Product类ZazzleProduct, VistaProduct
            type_review_cls: Review类ZazzleReview, VistaReview
        """
        try:
            # 初始化product
            product = type_product_cls(self.__product_url)

            # 通过商品页, 获得api请求参数
            review_api_params = product.get_review_api_params()

            # 上一步拿到的参数, 初始化review对象
            type_review = type_review_cls(review_api_params)

            review_list = list()

            for rating in self.__ratings:

                # 如果爬到的评论数量小于要求的数量
                if len(review_list) < self.__review_counts:
                    # 获取评论
                    review_list.extend(
                        type_review.get_reviews(rating=rating,
                                                review_counts=self.__review_counts - len(review_list)))

            logging.info('[RESULT] reviews count: ' + str(len(review_list)))

            # 如果爬到的数量大于this_new_product_ids的长度, 分段插入数据库
            if len(review_list) > len(self.__this_new_product_ids):
                CrawlerDB.insert_reviews(review_list=review_list, thisnew_product_ids=self.__this_new_product_ids, task_id=self.__task_id)
                logging.info('[SUCCESS] task_id = ' + str(self.__task_id))
            else:
                raise ReviewListError('review list less than thisnew product ids')

        except (RequestError, ReviewListError, Exception) as e:

            CrawlerDB.update_crawler_status_fail(self.__task_id)
            logging.error('[FAIL] task_id: ' + str(self.__task_id) + ', [REASON] set crawler status fail! ' + e.message, exc_info=True)


if __name__ == '__main__':

    r = redis.Redis(host=REDIS_ADDR, port=REDIS_PORT)

    while r.llen(REDIS_CRAWLER_KEY) > 0:
        pop_task = r.lpop(REDIS_CRAWLER_KEY)
        # r.rpush(REDIS_CRAWLER_KEY, pop_task)
        if pop_task is not None:
            task = json.loads(pop_task)

            task_product_url = task['weburl']
            task_review_counts = int(task['comments_count'])
            task_task_id = int(task['task_id'])
            task_crawler_type = int(task['platform'])
            task_ratings = list(map(int, task['ratings'].split(',')))
            task_this_new_product_ids = list(map(int, task['product_ids'].split(',')))

            if task_crawler_type == CrawlerType.ZAZZLE.value:
                task_crawler_type = CrawlerType.ZAZZLE
            else:
                task_crawler_type = CrawlerType.VISTA

            ReviewCrawler(
                product_url=task_product_url,
                review_counts=task_review_counts, task_id=task_task_id, crawler_type=task_crawler_type, ratings=task_ratings,
                this_new_product_ids=task_this_new_product_ids).get_reviews()
