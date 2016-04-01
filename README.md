# s3-bulk-transfer

Bulk transfer of objects into S3, for example from Akamai or another HTTP accessible data source, with preservation of Content-Type.

## Description

This tool was designed to help migrate from Akamai NetStorage to S3, where the Akamai objects were publically accessible.  It will preserve the  Content-Type header from the source.

Provide a list of URLs or paths for objects that are publically accessible via an HTTP GET, in a file defined by INPUT_FILE.  Generally you will mount a data folder to /input in the container.  You also specify a PART_NUMBER via the environment, or the command line.

The application will randomly partition the list of files into TOTAL_PARTS lists, and the container will work on only PART_NUMBER.  So you can for example launch 20 versions (TOTAL_PARTS=20), then launch with PART_NUMBER=1,2,3,...,20.  Before uploading an object it will test for it's existance in S3.  It does not check hash values.

The number of upload threads for each container is also configurable.  Under the hood, the application uses a shell command of the form:

```
curl -L http://source_domain/my-path | go3fr -m "Content-Type: video/mp4" -b my-bucket -k my-path
```

You can supply either paths, or full URLs.  The application will write out 3 files to the input directory upon completion:  bad_files, good_files, and existing_files.

## Configuration

ENVIRONMENT VARIABLES:

| Environment variable | Description |
| -------------------- | ----------- |
| UPLOADER_THREADS | number of upload threads, default=5
| AWS_ACCESS_KEY_ID | AWS credentials
| AWS_SECRET_ACCESS_KEY | AWS credentials
| TARGET_BUCKET | Target S3 bucket
| PART_NUMBER | Number from 1 to TOTAL_PARTS, representing a random chunk of the input paths (default=1)
| TOTAL_PARTS | Total number of parts the input file is being split into (default=1)
| INPUT_FILE | File with list of input paths, of the form "/foo/bar/baz.mpg", or full URLs (default=/input/paths.txt) 
| SOURCE_DOMAIN | Domain from which to pull the source files (e.g. the Akamai domain).  Only used for paths, not full URLs.
| SCHEME | One of http or https (default=http).  Only used for paths, not full URLs.


## Running

```
docker --env-file=my.env -v /home/me/input:/input reutersmedia/s3-bulk-transfer:latest
```