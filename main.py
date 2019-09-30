from database import CrawlerDB
from error import RequestError, ReviewListError

# 获得日志对象
from tools import get_logging, CrawlerType
from vista_reviews import VistaProduct, VistaReview
from zazzle_reviews import ZazzleProduct, ZazzleReview

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
        """调度方法"""

        product = type_product_cls(self.__product_url)
        review_api_params = product.get_review_api_params()

        type_review = type_review_cls(review_api_params)

        try:
            review_list = list()

            for rating in self.__ratings:
                if len(review_list) < self.__review_counts:
                    review_list.extend(
                        type_review.get_reviews(rating=rating,
                                                review_counts=self.__review_counts - len(review_list)))

            logging.info('total reviews count: ' + str(len(review_list)))
            if len(review_list) > len(self.__this_new_product_ids):
                CrawlerDB.insert_reviews(review_list=review_list, thisnew_product_ids=self.__this_new_product_ids)
                CrawlerDB.update_crawler_status_success(self.__task_id)
            else:
                raise ReviewListError('review list less than thisnew product ids')

        except (RequestError, ReviewListError):
            CrawlerDB.update_crawler_status_fail(self.__task_id)


if __name__ == '__main__':
    ReviewCrawler(
        product_url='https://www.vistaprint.com/signs-posters/foam-board-signs',
        review_counts=98, task_id=1, crawler_type=CrawlerType.VISTA, ratings=[5, 4, 3, 2, 1],
        this_new_product_ids=[110, 54]).get_reviews()

    ReviewCrawler(
        product_url='https://www.zazzle.com/pd/spp/pt-mojo_throwpillow?fabric=poly&style=16x16',
        review_counts=230, task_id=1, crawler_type=CrawlerType.ZAZZLE, ratings=[5, 4, 3, 2, 1],
        this_new_product_ids=[110, 54]).get_reviews()
