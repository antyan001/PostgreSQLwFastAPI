#!/usr/bin/env bash

mypass=lolkek123
DB=etldb
USER=anthony

apt-get -qq update && \
apt-get -q -y upgrade && \
apt-get install -y sudo curl \
                        wget \
                        locales \
                        gunicorn3 \
                        openssh-server \
                        openssh-client \
                        libmysqlclient-dev \
                        sshfs && \
rm -rf /var/lib/apt/lists/*

apt-get update -y && apt-get install -y python3.8-dev \
                                        python3.8-distutils \
                                        python3.8-venv \
                                        python3-setuptools \
                                        build-essential

# Register the version in alternatives
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1

# Set python 3 as the default python
update-alternatives --set python3 /usr/bin/python3.8

# Upgrade pip to latest version
curl -s https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3 get-pip.py --force-reinstall && \
    rm get-pip.py

python3.8 -m pip install --upgrade pip
python3 -m pip install --no-cache-dir -r requirements.txt
pip3 install --upgrade keyrings.alt

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