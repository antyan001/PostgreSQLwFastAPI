#!/usr/bin/env bash

mypass=lolkek123
DB=etldb
USER=anthony

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt -y install postgresql-12
systemctl status postgresql
sudo systemctl daemon-reload
sudo systemctl restart postgresql
sudo su - postgres -c "createdb $DB"
printf "$mypass\n$mypass" | sudo su - postgres -c "createuser -P -s -e $USER"

sudo -u postgres psql -c "grant all privileges on database $DB to $USER"

#sudo -u postgres psql -c 'select version();'
#sudo -u postgres psql -c '\l'

sudo apt install libpq-dev
sudo apt install -y python3-psycopg2
python3.8 -m pip install psycopg2==2.9.3