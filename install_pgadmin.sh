#!/usr/bin/bash

## Look at the file: /usr/pgadmin4/web/pgadmin/setup/user_info.py

#if all(value in os.environ for value in
#       ['PGADMIN_SETUP_EMAIL', 'PGADMIN_SETUP_PASSWORD']):
#    email = ''
#    p1 = ''
#    if os.environ['PGADMIN_SETUP_EMAIL'] \
#            and os.environ['PGADMIN_SETUP_PASSWORD']:
#        email = os.environ['PGADMIN_SETUP_EMAIL']
#        p1 = os.environ['PGADMIN_SETUP_PASSWORD']

pg_admin_email=ektovav@gmail.com
pg_admin_pwd=lolkek123

if [[ ! -d "$PGADMIN_SETUP_EMAIL" ]]; then
    echo 'setting PGADMIN ENV...'
    export PGADMIN_SETUP_EMAIL="${pg_admin_email}"
    export PGADMIN_SETUP_PASSWORD="${pg_admin_pwd}"
    echo "export PGADMIN_SETUP_EMAIL=${pg_admin_email}" >> ~/.bashrc
    echo "export PGADMIN_SETUP_PASSWORD=${pg_admin_pwd}" >> ~/.bashrc
fi

source ~/.bashrc

sudo apt-get remove -y pgadmin4
sudo apt-get remove -y pgadmin4-web

rm /var/lib/pgadmin/pgadmin4.db

sudo apt clean && \
sudo apt-get autoclean && \
sudo apt-get autoremove && \
sudo apt-get update

curl https://www.pgadmin.org/static/packages_pgadmin_org.pub | sudo apt-key add
sudo sh -c 'echo "deb https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/$(lsb_release -cs) pgadmin4 main" > /etc/apt/sources.list.d/pgadmin4.list && apt update'
apt install -y pgadmin4
sudo /usr/pgadmin4/bin/setup-web.sh --yes
sudo ufw allow 'Apache'
sudo ufw enable

sudo ufw allow 22

#then at your browser go to: http://65.108.60.87/pgadmin4