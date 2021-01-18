#!/bin/ash

set -x

syslog-ng --user root
redis-server --daemonize yes
goofys --region $AWS_S3_REGION $AWS_S3_BUCKET:assets $IT_STATIC_PATH
python rq_worker.py &
gunicorn wsgi_dashboard:app -b 0.0.0.0:$IT_DASHBOARD_PORT -k gevent -w 2 --timeout 200 --access-logfile=-

exec "$@"
