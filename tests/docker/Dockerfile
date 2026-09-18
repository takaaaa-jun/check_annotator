FROM ubuntu:latest

WORKDIR /home/ubuntu

RUN echo "sample" > sample.txt

#   hostのファイルをcontainerにこの名前でコピー
COPY copy.txt copy.txt

CMD [bin/bash]