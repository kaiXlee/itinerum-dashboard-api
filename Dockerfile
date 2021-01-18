FROM alpine:3.7
MAINTAINER Kyle Fitzsimmons "kfitzsimmons@gmail.com"

# install dependencies
RUN apk add git musl-dev gcc jpeg-dev libpq openssh redis postgresql-dev \
	py-pip py-virtualenv python python-dev zlib-dev fuse curl syslog-ng --no-cache
RUN pip install --upgrade pip

# install goofys for uploading to s3
WORKDIR /usr/local/bin
RUN mkdir /lib64 && ln -s /lib/libc.musl-x86_64.so.1 /lib64/ld-linux-x86-64.so.2
RUN curl -sL https://github.com/kahing/goofys/releases/download/v0.19.0/goofys > goofys && chmod a+x goofys
RUN mkdir /assets
ADD ./conf/syslog-ng.conf /etc/syslog-ng/

# install and run API (only installs dependencies when requirements.txt is edited)
WORKDIR /app
ADD ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY . /app
RUN ["chmod", "+x", "entrypoint.sh"]
ENTRYPOINT ["./entrypoint.sh"]