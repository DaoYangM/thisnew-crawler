# coding=utf-8


class CrawlerError(Exception):
    """爬虫异常基类"""

    def __init__(self, msg):
        super(CrawlerError, self).__init__(msg)
        self.msg = msg


class RequestError(CrawlerError):
    """requests请求失败3次时抛出此异常"""

    def __init__(self, msg):
        super(RequestError, self).__init__(msg)


class RequestParamError(CrawlerError):
    """正则获取不到api参数时抛出此异常"""

    def __init__(self, msg):
        super(RequestParamError, self).__init__(msg)


class ReviewListError(CrawlerError):
    """获取的评论数量少于thisnew_product_ids时抛出此异常"""

    def __init__(self, msg):
        super(ReviewListError, self).__init__(msg)
