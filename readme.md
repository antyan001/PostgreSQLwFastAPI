# ETL PyProject for NearRealTime(NRT) Data Stream Pipeline with PostGreSQL DB as backend and FastAPI with Async REST Endpoints

*PROJECT STRUCTURE*:
- `install_postgres.sh`: script for installing and configuring `PostgreSQL` DB on Ubuntu 
- `redis2postgres_insert.py`: py-script with connection to Postgres and implemented parallel loading of data rows being fetched from Redis cache 
- `service.py`: MAIN `FastAPI` async service running under uvicorn `ASGI` Web server providing async endpoints to fetch/modify/delete rows from PostgreSQL 
- `run.sh` : shell script for serving REST Endpoints under `Gunicorn` server producing load balancing with N workers and N threads  
- `/src/`
  - **./loader.py**: class with Postgres DB connection and build-in getter/loader methods for working with data rows 
  in parallel/nonparallel batch modes  

### Virtual Machines
Hosted virtual machines with installed databases (Redis/Postgres) and running microservises:
![virtual machines](./img/virt_machines.png)
Here Redis DB is located on one remote host and PostgreSQL is located in another remote machine.

### MAIN PROJECT DESCRIPTION
This project is considered as a continuation from previous implementation [RedisETL with Async FastAPI](https://github.com/antyan001/RedisETL) using predominately Redis DB for fast caching data at the backend.  
Hereafter we set up and run an instance of PostGres DB to catch data from key-val Redis cache and sore ones in prepared relation DB.
First we should connect to our DB name `etldb` with created user `anthony` having all grants as shown on the following picture: 
```postgresql
root@kcloud-production-user-136-vm-180:~/PostgresSQL# sudo -u postgres psql -c '\l'
could not change directory to "/root/PostgresSQL": Permission denied
                                  List of databases
   Name    |  Owner   | Encoding |   Collate   |    Ctype    |   Access privileges   
-----------+----------+----------+-------------+-------------+-----------------------
 etldb     | postgres | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =Tc/postgres         +
           |          |          |             |             | postgres=CTc/postgres+
           |          |          |             |             | anthony=CTc/postgres
 postgres  | postgres | UTF8     | en_US.UTF-8 | en_US.UTF-8 | 
 template0 | postgres | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =c/postgres          +
           |          |          |             |             | postgres=CTc/postgres
 template1 | postgres | UTF8     | en_US.UTF-8 | en_US.UTF-8 | =c/postgres          +
           |          |          |             |             | postgres=CTc/postgres
(4 rows)
```
Main class for PostgreSQL connection is implemented in script `loader.py`
```python
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
```
Firstly we should fetch all rows inserted into Redis cache sending the next POST request to remote service:
* --> *[POST]*: `/getTopNFromReplica`
```python
import shlex
cmd = 'curl -i http://65.108.56.136:8003/getTopNFromReplica -X POST -d "?replica=sample_us_users&topn=-1"'
args = shlex.split(cmd)
process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()

out_str = stdout.decode("utf-8").split("content-type: application/json")[-1].strip()
redis_getter_data = json.loads(out_str)


{'ab5ee960-39fc-482c-93e5-806e071bffc4': ['{"city": "Charleston", "state": "West Virginia", "country": "US", "postCode": "29492"}',
  '2020-05-19 05:20:32.212'],
 '3d8f9a3c-fca1-436a-9563-b206f301720a': ['{"city": "Indianapolis", "state": "Indiana", "country": "US", "postCode": "46254"}',
  '2020-09-09 15:32:20.030'],
 '15006991-51ed-4a8c-8199-22e6bb7ec09e': ['{"city": "Redlands", "state": "California", "country": "US", "postCode": "92374"}',
  '2020-06-27 09:32:17.307'],
 '1550596b-170d-46e2-8071-627cba76be68': ['{"city": "Clackamas", "state": "Oregon", "country": "US", "postCode": "97015"}',
  '2020-04-28 14:25:03.103'],
 '7f74dffe-db3b-406e-b082-e8653af20c56': ['{"city": "Zachary", "state": "Louisiana", "country": "US", "postCode": "70791"}',
  '2020-08-07 00:48:29.969']}
```
Main script `redis2postgres_insert.py` for communicating with PostGreSQL should be run in the following way:
``./redis2postgres_insert.py -parallel=[True|False]``

Next steps are:
- converting rows to pandas df and perform timestamp casting for columns with string timestamp
    ```python
            df = pd.DataFrame.from_dict(redis_getter_data, orient="index", columns=["address", "inserted_at"])
            df.reset_index(inplace=True)
            df.rename(columns={"index": "id"}, inplace=True)
            df['inserted_at'] = df['inserted_at'].apply(lambda x: pd.to_datetime(x))
    ``` 
- make type casting between pandas and Postgres
- create empty table in user defined scheme
- run batch loading (parallel/nonparallel) using `psycopg2` driver:
    ```python
            if useParallelLoader:
                db = PostGresDB(user="anthony", password="lolkek123", database="etldb")
                loader.push_rows_parallel(db, df, TBL_NAME, num_partitions=5, njobs=5, verbose=True)
            else:
                ## NonParallelized Bulk Insertion into DB
                loader.db_insert_batch(cur, TBL_NAME, cols_lst, values_list)
                db.connection.commit()
    ```
Check that all rows are commited succesully into user-defined scheme:
```python
root@kcloud-production-user-136-vm-180:~/PostgresSQL# ./redis2postgres_insert.py -parallel=True
2.9.3 (dt dec pq3 ext lo64)
('PostgreSQL 12.10 (Ubuntu 12.10-1.pgdg20.04+1) on x86_64-pc-linux-gnu, compiled by gcc (Ubuntu 9.3.0-17ubuntu1~20.04) 9.3.0, 64-bit',)
[Parallel(n_jobs=5)]: Using backend LokyBackend with 5 concurrent workers.
Pushed 999 lines 
Pushed 999 lines 
Pushed 999 lines 
Pushed 4 lines 
[Parallel(n_jobs=5)]: Done   4 out of   6 | elapsed:    2.5s remaining:    1.2s
Pushed 999 lines 
Pushed 999 lines 
[Parallel(n_jobs=5)]: Done   6 out of   6 | elapsed:    3.1s finished
                                     id                                            address             inserted_at
0  dc3c7f51-2ae0-40c6-88a0-84d74299bd4d  {"city": "Lincoln park", "state": "Michigan", ... 2020-08-05 21:14:33.994
1  d41459c4-92ae-46ed-a1c6-008e74a5186c  {"city": "Spring", "state": "Texas", "country"... 2020-11-25 16:55:37.199
2  ca005739-03ee-4993-bad0-0f311df1a29b  {"city": "Philadelphia", "state": "Pennsylvani... 2020-08-09 22:03:48.910
3  c6b52ccc-76bc-4ae7-a5e3-f755a74293d0  {"city": "Salisbury", "state": "North Carolina... 2020-06-01 23:20:31.093
4  4438a8eb-9e64-4405-a234-b3cc40a4b25d  {"city": "Lagrange", "state": "US-OUT", "count... 2020-08-15 23:13:51.984
```

Send signal to remove all records being successfully fetched and stored in Postgres DB:
* --> *[POST]*: `/clearRedisCache`
```python
# Send signal to clear Replica Cache in Redis
cmd = 'curl -i http://65.108.56.136:8003/clearRedisCache -X POST -d "?replica=sample_us_users&remove=True"'
args = shlex.split(cmd)
process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()
```
Wait for new data written to Redis cache and repeat all above-mentioned steps again.

## PostgreSQL monitoring: running Pgadmin on Virtual Server 
One can try to install pgAdmin in Ubuntu by running the following script: `install_pgadmin.sh`\
Next step is to configure and establish a connection to PostgreSQL via `pgadmin` GUI under created user: the user that was created at the final steps of Postgres configuration by running command\
`sudo su - postgres -c "createuser -P -s -e $USER"`\
After all configuraiton steps are complited one can run some query in Postgres QEditor :
![pgAdmin](./img/pgadmin.png)

## Serving PostgreSQL Database with REST API:
He we demonstrate the how to use developed Async CRUD (Create, Read, Update, and Delete) APIs using FastAPI functionality.\

MAIN REST script: ``service.py``

Fetch N rows from `sample_us_users` table uploaded at previous steps.
* --> *[GET]*: `http://65.108.60.87:8003/sample_us_users/?skip=0&take=5`
```python
cmd = 'curl -X GET http://65.108.60.87:8003/sample_us_users/?skip=0&take=5'
args = shlex.split(cmd)
process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()

out_str = stdout.decode("utf-8").split("content-type: application/json")[-1].strip()

json.loads(out_str)

[{'id': '3d4880db-8c73-4eb7-b0ec-d9c96d82dfab',
  'address': '{"city": "Sidney", "state": "Ohio", "country": "US", "postCode": "59270"}',
  'inserted_at': '2020-05-03T15:34:29.504000'},
 {'id': '472a0f40-fe20-4ee9-95aa-79cf5117f9ab',
  'address': '{"city": "Willingboro", "state": "New Jersey", "country": "US", "postCode": "08046"}',
  'inserted_at': '2020-03-14T23:41:04.324000'},
 {'id': '6338b020-b11f-491c-b1dc-5b3f8a980ef4',
  'address': '{"city": "Brenham", "state": "Texas", "country": "US", "postCode": "77833"}',
  'inserted_at': '2020-08-05T00:52:59.571000'},
 {'id': '6fe74d9f-5cb8-4be4-b02d-535df184fd63',
  'address': '{"city": "Addison", "state": "Illinois", "country": "US", "postCode": "60101"}',
  'inserted_at': '2019-05-07T18:14:56.131000'},
 {'id': 'd7c3e38c-77e2-4336-9803-cc264ee136c1',
  'address': '{"city": "Las Vegas", "state": "Nevada", "country": "US", "postCode": "89135"}',
  'inserted_at': '2020-06-01T21:35:16.507000'}]
``` 

Get a single Row given its Id via cURL using GET
* --> *[GET]*: `http://65.108.60.87:8003/sample_us_users/867a9975-cbd5-43dc-b3c9-49a4eddb870f/`
```python
cmd = 'curl -X GET http://65.108.60.87:8003/sample_us_users/867a9975-cbd5-43dc-b3c9-49a4eddb870f/'
args = shlex.split(cmd)
process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = process.communicate()

out_str = stdout.decode("utf-8").split("content-type: application/json")[-1].strip()

json.loads(out_str)

{'id': '867a9975-cbd5-43dc-b3c9-49a4eddb870f',
 'address': '{"city": "Riverdale", "state": "Georgia", "country": "US", "postCode": "30274"}',
 'inserted_at': '2020-07-15T16:57:53.897000'}
```

## GUNICORN support
Finally we used here a `GUNICORN` server for load balancing with 4 workers and 4 threads each with the full support of Graceful Shutdown and Graceful Reload.
Service side is propotyped on the base of: 
1. `Uvicorn` as ASGI web server implementation for Python.\
1. `FastAPI` implementation with `slowapi` `Limiter` to ratelimit API endpoint request in Fastapi application