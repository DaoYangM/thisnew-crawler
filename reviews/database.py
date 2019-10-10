# coding=utf-8

import pymysql
from reviews import config

from DBUtils.PooledDB import PooledDB
from pymysql.cursors import DictCursor

from reviews.tools import chunks, CrawlerStatus, get_logging

logging = get_logging()


class Mysql(object):
    __pool = None

    def __init__(self):
        self._conn = Mysql.__get_conn()
        self._cursor = self._conn.cursor()

    @staticmethod
    def __get_conn():
        if Mysql.__pool is None:
            Mysql.__pool = PooledDB(creator=pymysql, mincached=1, maxcached=20,
                                    host=config.HOST, user=config.USERNAME, passwd=config.PASSWORD, db=config.DB,
                                    port=config.PORT, charset=config.CHARSET, use_unicode=True, cursorclass=DictCursor)

        return Mysql.__pool.connection()

    def get_info(self, sql, param=None):
        """
        执行查询，并取出num条结果
        Args:
            sql: 查询ＳＱＬ，如果有查询条件，请只指定条件列表，并将条件值使用参数[param]传递进来
            param: 可选参数，条件列表值（元组/列表）

        Returns:
            result list/boolean 查询到的结果集
        """

        if param is None:
            info = self._cursor.execute(sql)
        else:
            info = self._cursor.execute(sql, param)
        if info > 0:
            result = self._cursor.fetchall()
        else:
            result = False
        return result

    def insert(self, sql, values):
        """
        向数据表插入多条记录
        Args:
            sql: 要插入的ＳＱＬ
            values: 要插入的记录数据tuple(tuple) / list[list]

        Returns:
            count 受影响的行数
        """

        try:
            self._cursor.execute(sql, values)
            self._conn.commit()
        except Exception as e:
            print('Error : {}'.format(e))
            self._conn.rollback()
        finally:
            self._cursor.close()
            self._conn.close()

    def insert_many(self, sql, data):
        """
        一次插入多个
        Args:
            sql: 要插入的ＳＱＬ
            data: 要插入的记录数据[(), ()] / ((), ())

        Returns:
            count 受影响的行数
        """
        try:
            self._cursor.executemany(sql, data)
            self._conn.commit()
        except Exception as e:
            print('Error : {}'.format(e))
            self._conn.rollback()
        finally:
            self._cursor.close()
            self._conn.close()

    def begin(self):
        """开启事务"""

        self._conn.begin()

    def end(self):
        """结束事务"""

        self._conn.commit()

    def dispose(self):
        """释放连接池资源"""

        self._cursor.close()
        self._conn.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        """撤销"""
        self._conn.rollback()

    @property
    def cursor(self):
        return self._cursor


class CrawlerDB:

    def __init__(self):
        pass

    @staticmethod
    def update_crawler_status_success(cursor, task_id):
        """
        更新爬虫状态为成功
        Args:
            cursor: mysql游标
            task_id: 主键
        """

        cursor.execute("UPDATE oc_review_catch_task SET task_status = %s WHERE task_id = %s",
                       (CrawlerStatus.SUCCESS.value, task_id))

    @staticmethod
    def update_crawler_status_fail(task_id):
        """
        更新爬虫状态为失败
        Args:
            task_id: 主键
        """
        mysql = Mysql()

        mysql.insert("UPDATE oc_review_catch_task SET task_status = %s WHERE task_id = %s",
                     (CrawlerStatus.FAIL.value, task_id))

    @staticmethod
    def clean_previous_reviews(cursor, thisnew_product_id):
        """
        清楚此product_id之前的评论, 避免插入重复评论
        Args:
            cursor: mysql游标
            thisnew_product_id: oc_product 主键id
        """

        cursor.execute("DELETE FROM oc_review WHERE customer_id = %s AND product_id = %s",
                       (config.CRAWLER_ID, thisnew_product_id))

    @staticmethod
    def insert_reviews(review_list, thisnew_product_ids, task_id):
        """
        批量插入爬取的评论, 按照len(thisnew_product_ids)的长度将review_list拆分成对应分组
        Args:
            review_list: 评论list
            thisnew_product_ids: thisnew商品id list
            task_id: 任务id
        """

        review_list = chunks(review_list, len(thisnew_product_ids))
        mysql = Mysql()
        mysql.begin()
        try:
            for index, thisnew_product_id in enumerate(thisnew_product_ids):
                values = list()

                CrawlerDB.clean_previous_reviews(mysql.cursor, thisnew_product_id)

                for review in review_list[index]:
                    value = (
                        thisnew_product_id, config.CRAWLER_ID, review.author, review.text, review.rating, 1,
                        review.date_add,
                        review.date_add)
                    values.append(value)

                mysql.cursor.executemany(
                    "INSERT INTO oc_review (product_id, customer_id, author, text, rating, status, date_added, date_modified) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    values)

            CrawlerDB.update_crawler_status_success(mysql.cursor, task_id)
            mysql.commit()
        except Exception as e:
            logging.error(e, exc_info=True)
            mysql.rollback()
        finally:
            mysql.dispose()
