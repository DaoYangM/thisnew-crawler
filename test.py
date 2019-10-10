# coding=utf-8

import threading

from main import ReviewCrawler
from reviews.tools import CrawlerType


def multi():
    task_product_url = 'http://vistaprint.com/marketing-materials/pens'
    task_review_counts = 10
    task_task_id = 15
    task_crawler_type = CrawlerType.VISTA
    task_ratings = [5, 4, 3, 2, 1]
    task_this_new_product_ids = [40]
    ReviewCrawler(
        product_url=task_product_url,
        review_counts=task_review_counts, task_id=task_task_id, crawler_type=task_crawler_type,
        ratings=task_ratings,
        this_new_product_ids=task_this_new_product_ids).get_reviews()


if __name__ == '__main__':

    for i in range(1):
        threading.Thread(target=multi, name='test' + str(i)).start()
