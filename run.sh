#!/usr/bin/bash

TIMEOUT=1000

result=`ps -a | grep -E "service*|gunicorn*" | awk '{print $1}' | wc -l`
if [ $result -ge 1 ]
   then
		process_id=$(ps -a | grep -E "service*|gunicorn*" | awk '{print $1}')
# 		echo 'Killing'
		for pid in $process_id; do
# 		    echo "KILL: $pid"
		    kill -9 $pid 2>&1>/dev/null
		    sleep 1
		done
   else
        echo "gunicorn is not running" >/dev/null
fi

nohup gunicorn --bind 0.0.0.0:8003 -w 4 --threads 4 --timeout $TIMEOUT -k uvicorn.workers.UvicornWorker service:app &