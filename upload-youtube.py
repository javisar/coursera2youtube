#!/usr/bin/env python
# -*- coding: utf-8 -*-

# python 2/3 compatibility imports
from __future__ import print_function
from __future__ import unicode_literals

try:
    from http.cookiejar import CookieJar
except ImportError:
    from cookielib import CookieJar

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

try:
    from urllib.request import urlopen
    from urllib.request import build_opener
    from urllib.request import install_opener
    from urllib.request import HTTPCookieProcessor
    from urllib.request import Request
    from urllib.request import URLError
except ImportError:
    from urllib2 import urlopen
    from urllib2 import build_opener
    from urllib2 import install_opener
    from urllib2 import HTTPCookieProcessor
    from urllib2 import Request
    from urllib2 import URLError

# we alias the raw_input function for python 3 compatibility
try:
    input = raw_input
except:
    pass

YOUTUBE_VIDEO_ID_LENGTH = 11

import argparse
import getpass
import json
import os
import os.path
import re
import sys
import random
import string
import unicodedata

validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)

def removeDisallowedFilenameChars(filename):
    cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
    return ''.join(c for c in cleanedFilename if c in validFilenameChars)

from subprocess import Popen, PIPE
from datetime import timedelta, datetime

from bs4 import BeautifulSoup

# Youtube
import httplib
import httplib2
import os
import sys

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google Developers Console at
# https://console.developers.google.com/.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "client_secrets.json"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the Developers Console
https://console.developers.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account.
YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
  message=MISSING_CLIENT_SECRETS_MESSAGE,
  scope=YOUTUBE_READ_WRITE_SCOPE)

storage = Storage("%s-oauth2.json" % sys.argv[0])
credentials = storage.get()

if credentials is None or credentials.invalid:
  flags = argparser.parse_args('')
  credentials = run_flow(flow, storage, flags)

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
  http=credentials.authorize(httplib2.Http()))



# To replace the print function, the following function must be placed before any other call for print
def print(*objects, **kwargs):
    """
    Overload the print function to adapt for the encoding bug in Windows Console.
    It will try to convert text to the console encoding before print to prevent crashes.
    """
    try:
        stream = kwargs.get('file', None)
        if stream is None:
            stream = sys.stdout
        enc = stream.encoding
        if enc is None:
            enc = sys.getdefaultencoding()
    except AttributeError:
        return __builtins__.print(*objects, **kwargs)
    texts = []
    for object in objects:
        try:
            original_text = str(object)
        except UnicodeEncodeError:
            original_text = unicode(object)
        texts.append(original_text.encode(enc, errors='replace').decode(enc))
    return __builtins__.print(*texts, **kwargs)

def get_page_contents(url, headers):
    """
    Get the contents of the page at the URL given by url. While making the
    request, we use the headers given in the dictionary in headers.
    """
    result = urlopen(Request(url, None, headers))
    try:
        charset = result.headers.get_content_charset(failobj="utf-8")  # for python3
    except:
        charset = result.info().getparam('charset') or 'utf-8'
    return result.read().decode(charset)


def directory_name(initial_name):
    import string
    allowed_chars = string.digits+string.ascii_letters+" _."
    result_name = ""
    for ch in initial_name:
        if allowed_chars.find(ch) != -1:
            result_name += ch
    return result_name if result_name != "" else "course_folder"



def get_filename(target_dir, filename_prefix):
    """ returns the basename for the corresponding filename_prefix """
    # this whole function is not the nicest thing, but isolating it makes
    # things clearer , a good refactoring would be to get
    # the info from the video_url or the current output, to avoid the
    # iteration from the current dir
    filenames = os.listdir(target_dir)
    subs_filename = filename_prefix
    for name in filenames:  # Find the filename of the downloaded video
        if name.startswith(filename_prefix):
            (basename, ext) = os.path.splitext(name)
            return basename

def parse_args():
    """
    Parse the arguments/options passed to the program on the command line.
    """
    parser = argparse.ArgumentParser(prog='upload-youtube',
                                     description='Upload videos to youtube',
                                     epilog='For further use information,'
                                     'see the file README.md',)

    # optional
    parser.add_argument('-p',
                        '--path',
                        dest='path',
                        action='store',
                        default=None,
                        help='path to the videos to upload')
    parser.add_argument('-n',
                        '--name',
                        dest='name',
                        action='store',
                        default=None,
                        help='name of the youtube playlist')
    parser.add_argument('-d',
                        '--description',
                        action='store',
                        dest='description',
                        help='description of the youtube playlist',
                        default=None)

    args = parser.parse_args()
    return args


# UPLOAD
from apiclient.http import MediaFileUpload

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def initialize_upload(youtube, options):
  tags = None
  if options.keywords:
    tags = options.keywords.split(",")

  body=dict(
    snippet=dict(
      title=options.title,
      description=options.description,
      tags=tags,
      categoryId=options.category
    ),
    status=dict(
      privacyStatus=options.privacyStatus
    )
  )

  # Call the API's videos.insert method to create and upload the video.
  insert_request = youtube.videos().insert(
    part=",".join(body.keys()),
    body=body,
    # The chunksize parameter specifies the size of each chunk of data, in
    # bytes, that will be uploaded at a time. Set a higher value for
    # reliable connections as fewer chunks lead to faster uploads. Set a lower
    # value for better recovery on less reliable connections.
    #
    # Setting "chunksize" equal to -1 in the code below means that the entire
    # file will be uploaded in a single HTTP request. (If the upload fails,
    # it will still be retried where it left off.) This is usually a best
    # practice, but if you're using Python older than 2.6 or if you're
    # running on App Engine, you should set the chunksize to something like
    # 1024 * 1024 (1 megabyte).
    media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
  )

  video_id = resumable_upload(insert_request)
  return video_id

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
  response = None
  error = None
  retry = 0
  while response is None:
    try:
      print("Uploading file...")
      status, response = insert_request.next_chunk()
      if 'id' in response:
        print("Video id '%s' was successfully uploaded." % response['id'])
      else:
        exit("The upload failed with an unexpected response: %s" % response)
    except HttpError, e:
      if e.resp.status in RETRIABLE_STATUS_CODES:
        error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                             e.content)
      else:
        raise
    except RETRIABLE_EXCEPTIONS, e:
      error = "A retriable error occurred: %s" % e

    if error is not None:
      print(error)
      retry += 1
      if retry > MAX_RETRIES:
        exit("No longer attempting to retry.")

      max_sleep = 2 ** retry
      sleep_seconds = random.random() * max_sleep
      print("Sleeping %f seconds and then retrying..." % sleep_seconds)
      time.sleep(sleep_seconds)
  return response['id']

class UploadOptions:
    def __init__(self, title, file, privacyStatus):
        self.file = file
        self.privacyStatus = privacyStatus
        self.keywords = None
        self.title = title
        self.description = None
        self.category = None


# MAIN

import re

TAG_RE = re.compile(r'<[^>]+>')
TAG_CH = re.compile(r'&[^;]+;')

def limit_string(string, length, fill=''):
    from textwrap import wrap
    return [s + fill for s in wrap(string, length - len(fill))]

def remove_tags(text):
    out = text.replace("<div>","").replace("</div>","\n")
    return TAG_CH.sub('',TAG_RE.sub('', out))
    
def main():
    args = parse_args()

    if not args.path or not args.name or not args.description:
        print("You must supply path AND name AND description")
        sys.exit(2)

   
    course_name = args.name
    course_description = args.description

    course_id = args.path.split('/')[len(args.path.split('/'))-1]
    course_url = "https://class.coursera.org/"+course_id
    print("course_id: %s" % course_id)
    print("course_url: %s" % course_url)

    
    head, tail = os.path.split(args.path)
    class_file = os.path.join(head,course_id+"-about.json")
    print("class_file: %s" % class_file)
    
    with open (class_file, "r") as myfile:
        content=myfile.read().replace('\n', '')

    #print("content: %s" % content)
    class_data = json.loads(content)
    course_name = class_data['name']

    course_description = "Complete.\n\n"+course_url+"\n\n"
    course_description += "Name: "+ class_data['name']+"\n"
    if 'instructor' in class_data: course_description += "Instructor: "+ class_data['instructor']+"\n"
    if 'estimatedClassWorkload' in class_data: course_description += "Workload: "+ class_data['estimatedClassWorkload']+"\n"
    course_description += "Coursera Id: "+ str(class_data['id']) +" ("+class_data['shortName']+")\n"
    
    if 'shortDescription' in class_data: course_description += "\nDescription:\n"+ class_data['shortDescription']+"\n"
    if 'recommendedBackground' in class_data: course_description += "\nRecommended Background:\n"+ remove_tags(class_data['recommendedBackground'])+"\n"
    #course_description += "\nCourse Format:\n"+ remove_tags(class_data['courseFormat'])+"\n"
    if 'suggestedReadings' in class_data: course_description += "\nSuggested Readings:\n"+ remove_tags(class_data['suggestedReadings'])+"\n"
    #course_description += "\nCourse Syllabus:\n"+ remove_tags(class_data['courseSyllabus'])+"\n"
    #course_description += "\nFaq:\n"+ remove_tags(class_data['faq'])+"\n"

    print("path: %s" % args.path)
    print("course_name: %s" % course_name)
    #print("course_description: \n%s" % course_description)    
    
    # This code creates a new, private playlist in the authorized user's channel.
    playlists_insert_response = youtube.playlists().insert(
      part="snippet,status",
      body=dict(
        snippet=dict(
          title=course_name,
          description=course_description
        ),
        status=dict(
          privacyStatus="unlisted"
        )
      )
    ).execute()
        
    playlist_id = playlists_insert_response["id"]
        
    print("Created playlist id: %s" % playlist_id)
    
    for dirname, dirnames, filenames in os.walk(args.path):
        # print path to all subdirectories first.
        #for subdirname in dirnames:
        #    print(os.path.join(dirname, subdirname))

        # print path to all filenames.
        for filename in filenames:
            #print(os.path.join(dirname, filename))
            if ".mp4" not in filename: continue
            full_path = os.path.join(dirname, filename)
            title = filename.replace(".mp4", "").replace("_", " ")
            print("Processing: %s" % title)
            
            options = UploadOptions(limit_string(title,99), full_path, VALID_PRIVACY_STATUSES[2])

            video_id = initialize_upload(youtube, options)            
            
            playlistItems_insert_response = youtube.playlistItems().insert(
              part="snippet",
              body=dict(
                snippet=dict(
                  playlistId=playlist_id,
                  resourceId=dict(
                    kind='youtube#video',
                    videoId=video_id
                  )
                )
              )
            ).execute()

    os.rename(args.path,os.join(head,removeDisallowedFilenameChars(course_name)))
    sys.exit(0)

# MAIN


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCTRL-C detected, shutting down....")
        sys.exit(0)
