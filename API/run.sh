#!/usr/bin/bash

sudo apt clean && \
sudo apt-get autoclean && \
sudo apt-get autoremove && \
sudo apt-get update

docker image prune -f && docker container prune -f

docker build -f Dockerfile . -t sqlalch_api #2>&1>/dev/null

## if we wanna run total rebuild and services restart -->
# docker rm -f $(docker ps -a -q) 2>&1>/dev/null
# docker run -d -p 6379:6379 docker.io/library/redis:latest /bin/sh -c 'redis-server --requirepass *****' 2>&1>/dev/null
# docker run -d -p 8001:8001 docker.io/redislabs/redisinsight:latest 2>&1>/dev/null

cd /root/PostgresSQL/API/

result=`docker ps -a | grep -E "sqlalch*" | awk '{print $1}' | wc -l`
if [ $result -ge 1 ]
   then
		process_id=$(docker ps -a | grep -E "sqlalch*" | awk '{print $1}')
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
           --env-file ./config.env --name sqlalch -d -p 0.0.0.0:8005:8005 docker.io/library/sqlalch_api:latest
