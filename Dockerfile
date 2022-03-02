#FROM python:3.8 as builder
FROM ubuntu:18.04
ENV PYTHONIOENCODING=utf-8
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
# RUN apt-get install -y tzdata && cp /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
ARG DEBIAN_FRONTEND=noninteractive

ARG mypass
ARG DB
ARG USER

RUN \
apt-get update -y && \
apt-get install -y apt-utils 2>&1 | \
                   grep -v "debconf: delaying package configuration, since apt-utils is not installed" && \
apt-get -qq update && \
apt-get -q -y upgrade && \
apt-get install -y sudo curl \
                        wget \
                        locales \
                        ca-certificates \
                        curl \
                        gnupg \
                        lsb-release \
                        gunicorn3 \
                        openssh-server \
                        openssh-client \
                        libmysqlclient-dev \
                        sshfs && \
rm -rf /var/lib/apt/lists/*

# Ensure that we always use UTF-8 and with Canadian English locale
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
RUN apt-get update -y && apt-get install -y python3.7-dev \
                                            python3.7-distutils \
                                            python3.7-venv \
                                            python3-setuptools \
                                            build-essential \
                                            libpq-dev

# Register the version in alternatives
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1

# Set python 3 as the default python
RUN update-alternatives --set python3 /usr/bin/python3.7

RUN sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
RUN wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
RUN apt-get update && \
    apt -y install postgresql-12
#RUN systemctl status postgresql
#    systemctl daemon-reload && \
#    sudo systemctl restart postgresql

COPY ./src /app
COPY . /app
WORKDIR /app

# Upgrade pip to latest version
RUN curl -s https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3 get-pip.py --force-reinstall && \
    rm get-pip.py

RUN python3.7 -m pip install --upgrade pip
RUN python3 -m pip install --no-cache-dir -r requirements.txt

#EXPOSE 8003

CMD  ["python3", "./dummy.py"]

#CMD ["/bin/sh", \
#     "-c", \
#     "gunicorn3 --bind 0.0.0.0:8003 -w 4 --threads 4 --timeout $TIMEOUT -k uvicorn.workers.UvicornWorker service:app" \
#    ]
