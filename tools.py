import logging
import math
import os
import re
from enum import Enum

import requests

from config import LOG_PATH
from error import RequestError

ZAZZLE_PATTERN = re.compile('zazzle', flags=re.I)
VISTA_PATTERN = re.compile('vista', flags=re.I)

# 请求失败重试次数
RETRY_COUNT = 3

# 初始化日志对象
# logging.basicConfig(filename=LOG_FILENAME, filemode='a', level=logging.INFO,
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class CrawlerStatus(Enum):
    """
    爬虫状态enum
        SUCCESS: 成功
        FAIL: 失败
    """

    SUCCESS = 2
    FAIL = 3


class CrawlerType(Enum):
    """
    爬虫类型enum
        ZAZZLE: 爬取zazzle
        VISTA: 爬取vistaprint
    """

    ZAZZLE = 1
    VISTA = 2


def request_resolver(url, params=None, header=None, cookies=None):
    """
    request请求封装, 请求如果失败将会重试 RETRY_COUNT 次
    Args:
        url: 请求url
        params: 请求参数
        header: 请求头
        cookies: cookies
    Returns:
        response对象
    Raises:
        RequestError: 请求失败超过 RETRY_COUNT 次 抛出此异常
    """
    retry_count = 0

    while retry_count < RETRY_COUNT:
        try:
            response = requests.get(url, params=params, headers=header,
                                    proxies={'http': 'socks5://127.0.0.1:1080',
                                             'https': 'socks5://127.0.0.1:1080'},
                                    cookies=cookies)
            if response.ok:
                return response
            else:
                raise requests.exceptions.RequestException

        except requests.exceptions.RequestException as e:
            msg = "request error " + str(retry_count) + " times url: " + url
            retry_count += 1
            logging.error(msg, exc_info=True)
            logging.error(e, exc_info=True)

        if retry_count == 3:
            raise RequestError(msg)


def review_resolver(review, crawler_type):
    """
    替换评论中的zazzle或vista关键字为thisnew, 并且去除评论中的表情
    Args:
        review: 评论内容
        crawler_type: 爬虫类型CrawlerType
    Returns:
        替换管关键字后并且去除表情的内容
    """

    if crawler_type == CrawlerType.ZAZZLE:
        return re.sub(ZAZZLE_PATTERN, 'thisnew', de_emoji(review))
    elif crawler_type == CrawlerType.VISTA:
        return re.sub(VISTA_PATTERN, 'thisnew', de_emoji(review))


def de_emoji(input_string):
    """
    去除评论中的表情
    Args:
        input_string: 原始评论内容

    Returns:
        去除表情符号的评论
    """

    return input_string.encode('ascii', 'ignore').decode('ascii')


def chunks(arr, m):
    """
    分段函数用于将arr分为m段
    Args:
        arr: 分段数组
        m: 分段个数

    Returns:
        分段后的arr数组
    """

    n = int(math.ceil(len(arr) / float(m)))
    return [arr[i:i + n] for i in range(0, len(arr), n)]


class Review:
    """评论对象"""

    def __init__(self, text, rating, author, date_add):
        """
        Args:
            text: 评价内容
            rating: 评价等级
            author: 评价人
            date_add: 评价时间
        """

        self.text = text
        self.rating = rating
        self.date_add = date_add
        self.author = author


def get_logging():
    """
    获取全局日志对象
    Returns: 全局日志logging对象
    """

    folder = os.path.exists(LOG_PATH)

    if not folder:
        os.makedirs(LOG_PATH)

    return logging.getLogger('')
