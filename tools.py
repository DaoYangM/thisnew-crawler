import math
import re

pattern = re.compile('zazzle', flags=re.I)


def review_resolver(review):
    return re.sub(pattern, 'thisnew', de_emoji(review))


def de_emoji(input_string):
    return input_string.encode('ascii', 'ignore').decode('ascii')


def chunks(arr, m):
    n = int(math.ceil(len(arr) / float(m)))
    return [arr[i:i + n] for i in range(0, len(arr), n)]


class Review:
    def __init__(self, text, rating, author, date_add):
        self.text = text
        self.rating = rating
        self.date_add = date_add
        self.author = author
