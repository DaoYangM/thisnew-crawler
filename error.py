class CrawlerError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg


class RequestError(CrawlerError):
    def __init__(self, msg):
        super().__init__(msg)


class ReviewListError(CrawlerError):
    def __init__(self, msg):
        super().__init__(msg)
