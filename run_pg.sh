#!/usr/bin/bash

DB=etldb
USER=anthony
mypass=lolkek123

sudo apt clean && \
sudo apt-get autoclean && \
sudo apt-get autoremove && \
sudo apt-get update

docker image prune -f && docker container prune -f

docker build --build-arg mypass="$mypass" \
             --build-arg DB="$DB" \
             --build-arg USER="$USER" \
             -f Dockerfile . -t postgres_app #2>&1>/dev/null

## if we wanna run total rebuild and services restart -->
# docker rm -f $(docker ps -a -q) 2>&1>/dev/null
# docker run -d -p 6379:6379 docker.io/library/redis:latest /bin/sh -c 'redis-server --requirepass *****' 2>&1>/dev/null
# docker run -d -p 8001:8001 docker.io/redislabs/redisinsight:latest 2>&1>/dev/null

cd /root/PostgresSQL/

result=`docker ps -a | grep -E "postgres_app*|pg_image*" | awk '{print $1}' | wc -l`
if [ $result -ge 1 ]
   then
		process_id=$(docker ps -a | grep -E "postgres_app*|pg_image*" | awk '{print $1}')
# 		echo 'Killing'
		for pid in $process_id; do
# 		    echo "KILL: $pid"
		    docker rm -f $pid 2>&1>/dev/null
		    sleep 1
		done
   else
        echo "docker is not running" >/dev/null
fi

docker run --device /dev/fuse \
           --cap-add SYS_ADMIN \
           --env-file ./config0.env --name pg_image -d -p 0.0.0.0:5432:5432 docker.io/library/postgres_app:latest

docker_id="$(docker ps -a | grep -E "pg_image*" | awk '{print $1}' | xargs)"; \
docker exec -it $docker_id /bin/sh -c "cd /app/; chmod u+x run_pg_server_conf.sh && ./run_pg_server_conf.sh"

#docker exec -it $docker_id /bin/sh -c "cd /app/; chmod u+x redis2postgres_insert.py &&./redis2postgres_insert.py -table=\"$TBL0\" -parallel=True"

#nohup gunicorn --bind 0.0.0.0:8003 -w 4 --threads 4 --timeout $TIMEOUT -k uvicorn.workers.UvicornWorker service:app &