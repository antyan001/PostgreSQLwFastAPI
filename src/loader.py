#!/usr/bin/python3.8

import os
import sys
import pandas as pd
import numpy as np
import shlex
import json
import decimal
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch, execute_values
import subprocess
from joblib import Parallel, delayed

class PostGresDB(object):

    def __init__(self, user, password, database):
        self.user = user
        self.password = password
        self.database = database

    def connect(self):
        self.connection = psycopg2.connect(database=self.database,
                                           user=self.user,
                                           password=self.password,
                                           host="localhost",
                                           port="5432")

        self.cursor = self.connection.cursor()

    def close(self):
        self.cursor.close()
        self.connection.close()

class PostGresLoader():

    def __init__(self):
        pass

    def dataTypeMapping(self, df, prim_indx= None):

        cols_specific = {}
        isDateFmt = False
        PRIMARY_INDX = prim_indx

        str_ = '''CREATE TABLE IF NOT EXISTS {0} ( '''
        for column_name, column in df.iteritems():
            try:
                if isinstance(column[column.first_valid_index()], str):
                    if (df[column_name].str.len().max() >= 4000):
                        #df.drop(columns=[column_name], inplace=True)
                        str_ += column_name.upper() + ' ' + 'CLOB, '
                        cols_specific[column_name] = ['CLOB', 'STRING']
                    else:
                        if 'ID' in column_name.upper() or 'ROW_ID' in column_name.upper():
                            max_len__ = df[column_name].str.len().max()
                            str_ += column_name.upper() + ' ' + 'VARCHAR({}), '.format(max_len__)
                            cols_specific[column_name] = ['VARCHAR({})'.format(max_len__), 'STRING']
                        else:
                            str_ += column_name.upper() + ' ' + 'VARCHAR(800), '
                            cols_specific[column_name] = ['VARCHAR(800)', 'STRING']
                elif isinstance(column[column.first_valid_index()], np.integer) and (column_name.upper() != "ROW_ID"):
                    if len(str(column[column.first_valid_index()])) < 1.e6:
                        str_ += column_name.upper() + ' ' + 'INTEGER, '
                        cols_specific[column_name] = ['INTEGER', 'INT']
                    else:
                        str_ += column_name.upper() + ' ' + 'INTEGER, '
                        cols_specific[column_name] = ['BIGINT', 'BIGINT']
                elif (
                        (isinstance(column[column.first_valid_index()], decimal.Decimal)) or
                        (isinstance(column[column.first_valid_index()], float))
                ):
                    #         df[column_name] = df[column_name].fillna(0.0)
                    str_ += column_name.upper() + ' ' + 'FLOAT, '
                    cols_specific[column_name] = ['FLOAT', 'FLOAT']
                elif (
                        isinstance(column[column.first_valid_index()], pd.Timestamp) or
                        isinstance(column[column.first_valid_index()], datetime.date)
                ):
                    if hasattr(column[column.first_valid_index()], 'minute'):
                        if column[column.first_valid_index()].minute == 0:
                            isDateFmt = True
                        else:
                            isDateFmt = False
                            str_ += column_name.upper() + ' ' + "TIMESTAMP, "
                            cols_specific[column_name] = ['TIMESTAMP', 'DATE_FORMAT({}, "yyyy-MM-dd HH:mm:ss")']
                    else:
                        isDateFmt = True
                    if isDateFmt:
                        str_ += column_name.upper() + ' ' + "DATE, "
                        cols_specific[column_name] = ['DATE', 'DATE_FORMAT({}, "yyyy-MM-dd")']
                else:
                    None
            except:
                str_ += column_name.upper() + ' ' + 'VARCHAR(800), '
                cols_specific[column_name] = ['VARCHAR(800)', 'STRING']

        res = str_.strip()[:-1] + ' )'

        cr_tbl_sql = res

        return cr_tbl_sql

    def _corpora_iter(self, df, num_partitions=15):
        len_batches = len(df) // num_partitions
        if len(df) % num_partitions:
            num_partitions += 1
        for i in range(num_partitions):
            __start = i * len_batches
            __end = min((i + 1) * len_batches, len(df))
            yield df.loc[__start:__end - 1, :]

    def _commitrows_many(self, args):
        df, db, tblname = args
        db.connect()
        cur = db.cursor
        rows = df.values.tolist()
        cols_lst = df.columns.tolist()
        self.db_insert_batch(cur, tblname, cols_lst, rows)
        db.connection.commit()
        print('Pushed {} lines '.format(len(df)))

    def db_insert_batch(self, curs, tblname, cols_lst, values_list):
        joined_cols_str = ", ".join(cols_lst)
        sql = """
            INSERT INTO {tbl} ({cols})
            VALUES %s
        """.format(tbl=tblname, cols=joined_cols_str)

        execute_values(curs, sql, values_list, page_size=1000)

    def push_rows_parallel(self, db, df=None, tblname=None, num_partitions=10, njobs=1, verbose=True):

        Parallel(n_jobs=njobs, verbose=verbose)(
            map(delayed(self._commitrows_many), [(__iter, db, tblname) for __iter in self._corpora_iter(df, njobs)]))
