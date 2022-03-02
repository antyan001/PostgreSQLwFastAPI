#!/usr/bin/env bash

#chmod -R 0700 /var/lib/postgresql/12/main
#chmod +r /etc/postgresql/12/main/pg_hba.conf
#chown postgres -R /var/lib/postgresql/12/main/
#log=$(tail /var/log/postgresql/postgresql-12-main.log) && echo "$log"

echo "listen_addresses = '*'" >> /etc/postgresql/12/main/postgresql.conf
echo "host    all             all             65.108.60.0/24          md5" >> /etc/postgresql/12/main/pg_hba.conf
echo "host    all             all             172.17.0.0/24           md5" >> /etc/postgresql/12/main/pg_hba.conf

service postgresql restart
sudo pg_ctlcluster 12 main start
#pg_lsclusters

su - postgres -c "createdb $database_name"
printf "$db_password\n$db_password" | sudo su - postgres -c "createuser -P -s -e $db_username"
sudo -u postgres psql -c "grant all privileges on database $database_name to $db_username"