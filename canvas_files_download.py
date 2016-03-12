#!/usr/bin/env python3

import argparse
import requests
import re
import json
import os.path
import sys
from http.cookiejar import LWPCookieJar
import auckland_auth
import util

FILES = list()

def get_folders(session):
    """Retrieve the list of top level folders available to the user on canvas"""
    # TODO is this header necessary?
    header = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, sdch",
        "Accept-Language": "en-US,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Host": "canvas.auckland.ac.nz",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/48.0.2564.116 Chrome/48.0.2564.116 Safari/537.36"
    }
    response = session.get("https://canvas.auckland.ac.nz/files", headers=header, allow_redirects=True, verify=True)
    pattern = re.compile('(ENV = )({.*})(;)')
    match = pattern.search(response.text)
    if match:
        files_string = match.group(2)
        json_files = json.loads(files_string)
    else:
        print("Regex failed")
    # TODO handle files in root directory (does canvas even allow this?)
    # Iterate through dictionary
    for item in json_files['FILES_CONTEXTS']:
        print("Processing %s" % item['name'])
        base_url = "https://canvas.auckland.ac.nz/api/v1/"
        url = None
        patterns = {
            "user": re.compile('(user)(_)([0-9]*)'),
            "course": re.compile('(course)(_)([0-9]*)'),
            "group": re.compile('(group)(_)([0-9]*)')
        }
        for storage_type in patterns.keys():
            match = patterns[storage_type].match(item['asset_string'])
            if match:
                identifier = match.group(3)
                url = base_url + storage_type + "s/" + identifier + "/folders/root"
                recurse_folder(session, url, item['name'])
                break
        else:
            # Didn't match known resource type
            print("Unknown resource type '%s', skipping" % str(item['asset_string']))


def recurse_folder(session, folder_url, prefix):
    """Recursively process contents of folder"""
    response = session.get(folder_url, verify=True)
    if response.status_code != 200:
        print("HTTP" + str(response.status_code) + " failed to get folder listing: " + response.text)
        return
    response_cleaned = response.text.split(';', 1)[1]
    response_json = json.loads(response_cleaned)
    try:
        files_url = response_json['files_url']
        process_files(session, files_url, prefix)
    except KeyError:
        # Folder has no files in it
        pass
    try:
        folders_url = response_json['folders_url']
        response = session.get(folders_url, verify=True)
        response_cleaned = response.text.split(';', 1)[1]
        response_json = json.loads(response_cleaned)
        for item in response_json:
            name = item['name']
            url = os.path.dirname(item['folders_url'][:-7])
            recurse_folder(session, url, os.path.join(prefix, name))
    except KeyError:
        # Folder has no folders in it
        pass


def process_files(session, files_url, folder_prefix):
    """Retrieve the file listing and contruct canonical file paths for each file"""
    response = session.get(files_url, verify=True)
    response_cleaned = response.text.split(';', 1)[1]
    response_json = json.loads(response_cleaned)
    for item in response_json:
        cannonical = os.path.join(folder_prefix,item['display_name'])
        url = item['url']
        FILES.append((url, cannonical))


def download_files(session):
    """Download files in list to the corresponding location"""
    for item in FILES:
        url = item[0]
        filename = item[1]
        util.download(session, url, filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Retrieve all your files from University of Auckland Canvas')
    parser.add_argument('username', help='Canvas username')
    parser.add_argument('password', help='Canvas password')
    args = parser.parse_args()
    session = auckland_auth.authenticate("https://canvas.auckland.ac.nz", args.username, args.password)
    get_folders(session)
    download_files(session)
    print("All files have been retrieved")

