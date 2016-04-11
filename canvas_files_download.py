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
import threading
import multiprocessing

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
    jobs = list()
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
                thread = threading.Thread(target=recurse_folder, args=( session, url, clean(item['name']) ) )
                thread.start()
                jobs.append(thread)
                break
        else:
            # Didn't match known resource type
            print("Unknown resource type '%s', skipping" % str(item['asset_string']))
    for job in jobs:
        job.join()


def recurse_folder(session, folder_url, prefix):
    """Recursively process contents of folder"""
    # TODO handle case where foldername has invalid characters (e.g path seperators such as / for *nix systems)
    response = session.get(folder_url, verify=True)
    if response.status_code != 200:
        print("HTTP" + str(response.status_code) + " failed to get folder listing: " + response.text)
        return
    response_cleaned = response.text.split(';', 1)[1]
    response_json = json.loads(response_cleaned)
    try:
        files_url = response_json['files_url']
        files_count = response_json['files_count']
        # TODO seems there is a limit of 100 items per page. Need to introduce pagination supprt
        if files_count > 0:
            files_url += "?per_page=%d" % files_count
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
            recurse_folder(session, url, os.path.join(prefix, clean(name)))
    except KeyError:
        # Folder has no folders in it
        pass


def process_files(session, files_url, folder_prefix):
    """Retrieve the file listing and construct canonical file paths for each file"""
    response = session.get(files_url, verify=True)
    response_cleaned = response.text.split(';', 1)[1]
    response_json = json.loads(response_cleaned)
    for item in response_json:
        cannonical = os.path.join(folder_prefix, clean(item['display_name']))
        url = item['url']
        # append() is thread-safe
        FILES.append((url, cannonical))


def download_files(session, verbose):
    """Download files in list to the corresponding location"""
    print("Starting download")
    jobs = list()
    core_count = multiprocessing.cpu_count()
    chunk_size = len(FILES) // core_count
    remainder = len(FILES) % core_count
    for i in range(1, core_count+1):
        start = (i-1)*chunk_size
        end = i*chunk_size
        sub_list = FILES[start:end]
        thread = threading.Thread(target=do_chunk, args=(sub_list, verbose))
        thread.start()
        jobs.append(thread)
    if core_count*chunk_size < len(FILES):
        sub_list = FILES[core_count*chunk_size:]
        thread = threading.Thread(target=do_chunk, args=(sub_list, verbose))
        thread.start()
        jobs.append(thread)
    for job in jobs:
        job.join()

def do_chunk(file_list, verbose):
    for item in file_list:
        url = item[0]
        filename = item[1]
        if not url:
            print("There is no url available for '%s', so cannot download it" % filename)
            continue
        util.download(session, url, filename, verbose=verbose)



def clean(string):
    """Clean a file or folder name of characters that are not allowed"""
    pre = string
    string = re.sub('[^\w\-_\.(): ]', '_', string)
    return string

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Retrieve all your files from University of Auckland Canvas')
    parser.add_argument('username', help='Canvas username')
    parser.add_argument('password', help='Canvas password')
    parser.add_argument('--show-existing', action='store_true', help='List files found on Canvas even if they exist on disk')
    args = parser.parse_args()
    session = auckland_auth.authenticate("https://canvas.auckland.ac.nz", args.username, args.password)
    get_folders(session)
    download_files(session, args.show_existing)
    print("All files have been retrieved")

