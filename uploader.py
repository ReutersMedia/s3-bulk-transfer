import sys
import os
import Queue
import threading
import subprocess
import urllib2
import time

from boto.s3.connection import S3Connection

import logging

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

_bad_files = []
_good_files = []
_existing_files = []

def is_url(x):
    return x.split(':')[0].lower() in ('http','https')

def build_file_queue(q,part_n):
    in_f = open(os.getenv("INPUT_FILE"),'r')
    total_parts = int(os.getenv("TOTAL_PARTS"))
    n_paths = 0
    while True:
        line = in_f.readline()
        if line=='':
            break
        line = line.strip()
        if line=='':
            continue
        if hash(line)%total_parts == (part_n - 1):
            q.put(line)
            n_paths += 1
    LOGGER.info("total objects to process: {0}".format(n_paths))
    
def get_content_type(url):
    req = urllib2.Request(url)
    req.get_method = lambda : 'HEAD'
    resp = urllib2.urlopen(req,timeout=20)
    return resp.info().getheader('Content-Type')

def check_s3_object_exists(bucket,path):
    if is_url(path):
        path = urllib.splitquery(urllib.splithost(urllib.splittype(path)[1])[1])[0]
    return (bucket.get_key(path)!=None)
    

def do_upload(path,source_domain,target_bucket,bucket,scheme):
    LOGGER.info("Processing {0}".format(path))
    try:
        if is_url(path):
            source_url=path
        else:
            if path.startswith('/'):
                path = path[1:]
            source_url = "{0}://{1}/{2}".format(scheme,source_domain,path)
        if check_s3_object_exists(bucket,path):
            LOGGER.info("S3 object already exists: {0}".format(path))
            _existing_files.append(path)
            return
        content_type = get_content_type(source_url)
        if content_type:
            ct_arg = "-m \"Content-Type: {0}\"".format(content_type)
        else:
            ct_arg = ""
        cmd = "curl -L {0} | gof3r put {1} -b {2} -k \"{3}\"".format(
            source_url,
            ct_arg,
            target_bucket,
            path)
        LOGGER.info("upload command: {0}".format(cmd))
        t_start = time.time()
        subprocess.check_output(cmd, shell=True)
        t_elapsed = time.time()-t_start
        LOGGER.info("finished uploading {0} in {1} sec".format(path,t_elapsed))
        _good_files.append(path)
    except urllib2.HTTPError, ex:
        LOGGER.error("Error downloading path {0}".format(path))
        _bad_files.append(path)
    except Exception, ex:
        LOGGER.exception("Error processing path {0}".format(path))
        _bad_files.append(path)
        
def run(num_threads,part_num):
    LOGGER.info("Starting {0} threads".format(num_threads))
    q = Queue.Queue()
    source_domain = os.getenv("SOURCE_DOMAIN")
    target_bucket = os.getenv("TARGET_BUCKET")
    scheme = os.getenv("SCHEME")
    def worker():
        # separate connection and bucket for each worker
        s3conn = S3Connection()
        bucket = s3conn.get_bucket(target_bucket)
        while True:
            path = q.get()
            if path==None:
                break
            do_upload(path,source_domain,target_bucket,bucket,scheme)
            q.task_done()
        LOGGER.info("Exiting worker")
        
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)

    try:
        build_file_queue(q,part_num)
        q.join()
    except:
        LOGGER.exception("Error building file queue, exiting")
        sys.exit(1)

    [ q.put(None) for _ in range(num_threads) ]
    for t in threads:
        t.join()
        
    LOGGER.info("done.  number good={0}, bad={1}, existing={2}".format(len(_good_files),len(_bad_files),len(_existing_files)))
    with open('/input/good.txt','w') as good_f:
        [good_f.write(x+'\n') for x in _good_files]
    with open('/input/bad.txt','w') as bad_f:
        [bad_f.write(x+'\n') for x in _bad_files]
    with open('/input/existing.txt', 'w') as ex_f:
        [ex_f.write(x+'\n') for x in _existing_files]
        
USAGE = """
usage: docker run -v dir-with-input-file:/input image-name

Parellel multipart and multhreaded transfer of assets from URLs to S3, useful for migrating from Akamai to AWS.
After completion, will emit a list of good and bad transfers to /input/good.txt and /input/bad.txt


ENVIRONMENT VARIABLES:

UPLOADER_THREADS       number of upload threads, default=5
AWS_ACCESS_KEY_ID      AWS credentials
AWS_SECRET_ACCESS_KEY  AWS credentials
TARGET_BUCKET          Target S3 bucket
PART_NUMBER            Number from 1 to TOTAL_PARTS, representing a random chunk of the input paths (default=1)
TOTAL_PARTS            Total number of parts the input file is being split into (default=1)
INPUT_FILE             File with list of input paths, of the form "/foo/bar/baz.mpg", or full URLs (default=/input/paths.txt) 
SOURCE_DOMAIN          Domain from which to pull the source files (e.g. the Akamai domain).  Only used for paths, not full URLs.
SCHEME                 One of http or https (default=http).  Only used for paths, not full URLs.


The PART_NUMBER can also be supplied as an argument.
"""
    
if __name__=="__main__":
    if not os.path.exists(os.getenv("INPUT_FILE")):
        print "Input file {0} not found".format(os.getenv("INPUT_FILE"))
        print ""
        print USAGE
        sys.exit(1)
    if len(sys.argv)>=2 and sys.argv[1]=='usage':
        print USAGE
        sys.exit(0)
    if len(sys.argv)>=2:
        part_num = int(sys.argv[1])
    else:
        part_num = int(os.getenv("PART_NUMBER"))
    run(int(os.getenv("UPLOADER_THREADS")),part_num)
        
