FROM alpine:3.3

RUN apk update && \
    apk upgrade && \
    apk add python curl py-pip && \
    pip install boto && \
    cd /tmp && \
    curl -sSL https://github.com/rlmcpherson/s3gof3r/releases/download/v0.5.0/gof3r_0.5.0_linux_amd64.tar.gz | tar -xvz && \
    mv /tmp/gof3r*/gof3r /usr/local/bin/gof3r 

ENV UPLOADER_THREADS=5 \
    AWS_ACCESS_KEY_ID=changeme \
    AWS_SECRET_ACCESS_KEY=changeme \
    TARGET_BUCKET=changeme \
    PART_NUMBER=1 \
    TOTAL_PARTS=1 \
    INPUT_FILE=/input/paths.txt \
    SOURCE_DOMAIN=changeme \
    SCHEME=http

COPY uploader.py /root/uploader.py

ENTRYPOINT ["python", "/root/uploader.py"]

# pass in "all", "1", "2"
CMD [""]