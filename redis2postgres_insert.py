#!/usr/bin/python3

import os
import sys
import re
import pandas as pd
import numpy as np
import shlex
import json
import psycopg2
import argparse

from psycopg2.extras import execute_batch, execute_values
import subprocess
from joblib import Parallel, delayed
from src import PostGresDB, PostGresLoader

if __name__ == '__main__':

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-table', '--tableName', type=str, required=True, default=False)
    parser.add_argument('-parallel', '--runParallel', type=bool, required=True, default=False)
    parser.add_argument('-h', '--help',
                        action='help', default=argparse.SUPPRESS,
                        help='set runParallel param to True if you wanna apply parallel pool for batch insert into')
    args = parser.parse_args()

    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    TBL_NAME = args.tableName  # "sample_us_users"
    NAT_SUBST_STR__ = "9999-01-01"
    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    if args.runParallel:
        useParallelLoader = True
    else:
        useParallelLoader = False

    print(psycopg2.__version__)

    ## Load Instance from Main PostGres Loader CLS
    loader = PostGresLoader()

    ## Connect to PostrGres DB
    db = PostGresDB(user="anthony", password="lolkek123", database="etldb")
    db.connect()
    cur = db.cursor

    cur.execute("select version();")
    res = cur.fetchone()
    print(res)

    ## FastApi REST Endpoint to Redis DB
    ## Fetch all COLUMN NAMES from cache corresponding to table of interest
    cmd = 'curl -i http://65.108.56.136:8003/getReplicaColumns -X POST -d "?replica={}"'.format(TBL_NAME)
    args = shlex.split(cmd)
    process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    out_str = stdout.decode("utf-8").split("content-type: application/json")[-1].strip()
    ## First col is index in Redis cache so we should take it off
    redis_getter_cols = json.loads(out_str)[1:]

    ## FastApi REST Endpoint to Redis DB
    ## Fetch all records from cache
    cmd = 'curl -i http://65.108.56.136:8003/getTopNFromReplica -X POST -d "?replica={}&topn=-1"'.format(TBL_NAME)
    args = shlex.split(cmd)
    process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    out_str = stdout.decode("utf-8").split("content-type: application/json")[-1].strip()
    redis_getter_data = json.loads(out_str)

    if len(redis_getter_data) > 0:
        ## Transforn Rows to Pandas
        df = pd.DataFrame.from_dict(redis_getter_data, orient="index", columns=redis_getter_cols)
        df.reset_index(inplace=True)
        df.rename(columns={"index": "id"}, inplace=True)

        ## Find DateTime col in String Notation and cast it to DateTime Type
        datetime_cols = []
        find_datetime = re.compile("\d{4}\-\d{2}\-\d{2}\s*\d{2}\:\d{2}\:\d{2}\.?\d{1,6}?")

        for col in df.columns:
            touch_df_rec = df[col][df[col].first_valid_index()]
            try:
                out = find_datetime.findall(touch_df_rec)
                if len(out) > 0:
                    datetime_cols.append(col)
            except:
                pass

        if len(datetime_cols) > 0:
            for col in datetime_cols:
                df[col] = df[col].apply(lambda x: pd.to_datetime(x))

        dct4rename = {col: re.sub("\.","_", col) for col in df.columns}
        datetime_cols = [re.sub("\.", "_", col) for col in datetime_cols]
        df.rename(columns=dct4rename, inplace=True)

        ###########################################################################
        ## !!!!!!!!!!!!!!!!!!! REPLACING pd.NaT VALUES WITH None!!!!!!!!!!!!!!!!!##
        ###########################################################################
        for col in datetime_cols:
            df[col] = df[col].astype(object).where(df[col].notnull(), None)
            # df.replace({np.NaN: pd.to_datetime(NAT_SUBST_STR__)}, inplace = True)
            # df = df.replace({pd.NaT: None}).replace({np.NaN: None})

        values_list = df.values.tolist()
        cols_lst = df.columns.tolist()

        ## Types auto mapping between pandas and Postrgres and `CREATE TABLE` clause builder
        cr_sql_query = loader.dataTypeMapping(df)

        ## CREATE Table following with Bulk Isert Into
        cur.execute("DROP TABLE IF EXISTS {} ".format(TBL_NAME))

        # query= \
        # '''
        # CREATE TABLE IF NOT EXISTS {} (
        #                   id VARCHAR(100),
        #                   address VARCHAR(1000) NOT NULL,
        #                   inserted_at TIMESTAMP NOT NULL
        #  );
        # '''.format(TBL_NAME)

        query = cr_sql_query.format(TBL_NAME)

        cur.execute(query)
        db.connection.commit()
        db.close()

        if useParallelLoader:
            db = PostGresDB(user="anthony", password="lolkek123", database="etldb")
            loader.push_rows_parallel(db, df, TBL_NAME, num_partitions=5, njobs=5, verbose=True)
        else:
            ## NonParallelized Bulk Insertion into DB
            loader.db_insert_batch(cur, TBL_NAME, cols_lst, values_list)
            db.connection.commit()

        # cur.execute("select * from {};".format(TBL_NAME))
        # res = cur.fetchmany()

        ## Query some data from newly updated table of interest
        db = PostGresDB(user="anthony", password="lolkek123", database="etldb")
        db.connect()
        cur = db.cursor
        rnd_dt_col = datetime_cols[np.random.randint(0,len(datetime_cols))]
        query='''select * from {} 
                 where {} > to_timestamp('2021-06-01 00:00:00', 
                                         'YYYY-MM-DD HH24:MI:SS')
              '''.format(TBL_NAME, rnd_dt_col)

        cur.execute(query)
        res = cur.fetchmany(20)
        out_df = pd.DataFrame(res, columns=cols_lst)
        print(out_df.head())

        # Close connection to DB
        db.close()

        # Send signal to clear Replica Cache in Redis
        # cmd = 'curl -i http://65.108.56.136:8003/clearRedisCache -X POST -d "?replica=sample_us_users&remove=True"'
        # args = shlex.split(cmd)
        # process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # stdout, stderr = process.communicate()