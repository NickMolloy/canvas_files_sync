#!/usr/bin/env python3

import argparse
import requests
import requests.utils
import pickle
import re
import json
import os.path
import urllib
import sys
from http.cookiejar import LWPCookieJar

FILES = list()

def authenticate(username, pasword):
    """Use the username and password to authenticate to auckland university canvas, and return
    a requests session object with all needed cookies
    """
    # TODO check http response code for each request
    # Try to load existing session from disk
    session = get_cookies()
    if session:
        return session
    # Create session
    session = requests.Session()
    session.cookies = LWPCookieJar('.cookiejar')
    # Make initial request to canvas
    response = session.get("https://canvas.auckland.ac.nz", allow_redirects=True, verify=True)
    response = session.get("https://iam.auckland.ac.nz/Authn/UserPassword", allow_redirects=True, verify=True)
    # Send credentials
    form_data = {
        'submitted': '1',
        'j_username': username,
        'j_password': pasword
    }
    response = session.post("https://iam.auckland.ac.nz/Authn/UserPassword", data=form_data, allow_redirects=True, verify=True)
    # Need to parse SamlRepsone from response body
    pattern = re.compile('(<input type="hidden" name="SAMLResponse" value=")(.*)(")')
    match = pattern.search(response.text)
    SAMLResponse = match.group(2)
    # Send SamlRepsone
    form_data = {
        'SAMLResponse' : SAMLResponse
    }
    response = session.post("https://canvas.auckland.ac.nz/saml_consume", data=form_data, allow_redirects=True, verify=True)
    response = session.get("https://iam.auckland.ac.nz/profile/SAML2/Redirect/SSO", allow_redirects=True, verify=True)
    # Save the cookies to disk
    session.cookies.save(ignore_discard=True)
    return session


def get_cookies():
    """Retrieve cookie jar from disk if it exists and return a session containing it, else return none"""
    # TODO check expiration of cookies
    session = requests.Session()
    session.cookies = LWPCookieJar('.cookiejar')
    if os.path.exists('.cookiejar'):
        # Load cookies, including ones with the discard flag
        session.cookies.load(ignore_discard=True)
        return session
    else:
        return None


def get_folders(session):
    """Retrieve the list of top level folders available to the user on canvas"""
    header = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, sdch",
        "Accept-Language": "en-US,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Host": "canvas.auckland.ac.nz",
        "Pragma": "no-cache",
        "Referer": "https://canvas.auckland.ac.nz/files/folder/user_43529",
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
        user_pattern = re.compile('(user)(_)([0-9]*)')
        course_pattern = re.compile('(course)(_)([0-9]*)')
        match = course_pattern.match(item['asset_string'])
        if not match:
            # Probably a user
            match = user_pattern.match(item['asset_string'])
            if match:
                # Is a user resource
                url = base_url + "users/" + match.group(3) + "/folders/root"
            else:
                # Neither a user nor course
                print("Unknown resource type '%s', skipping" % str(item['asset_string']))
                continue
        else:
            # Is a course resource
            url = base_url + "courses/" + match.group(3) + "/folders/root"
            #url = base_url + "folders/" + match.group(3) + "/folders"
        recurse_folder(session, url, item['name'])


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
        #print("Files url: " + files_url)
        process_files(session, files_url, prefix)
    except KeyError:
        # Folder has no files in it
        pass
    try:
        folders_url = response_json['folders_url']
        #print("Folders url: " + folders_url)
        response = session.get(folders_url, verify=True)
        response_cleaned = response.text.split(';', 1)[1]
        response_json = json.loads(response_cleaned)
        for item in response_json:
            name = item['name']
            url = item['folders_url'][:-7]
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
        # Check if file already exists on disk
        if os.path.exists(filename):
            print(filename + " already exists on disk")
            continue
        # Make needed directory
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        # Start download
        response = session.get(url, stream=True, verify=True)
        total_length = int(response.headers.get('content-length'))
        progress = 0
        print("Downloading: " + filename)
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=20480): 
                if chunk: # filter out keep-alive new chunks
                    progress += len(chunk)
                    f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())
                    done = int(50 * progress / total_length)
                    sys.stdout.write("\r[%s%s] %s" % ('=' * done, ' ' * (50-done), 'Progress: ' + str(done * 2) + '%') )    
                    sys.stdout.flush()
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Retrieve all your files from University of Auckland Canvas')
    parser.add_argument('username', help='Canvas username')
    parser.add_argument('password', help='Canvas password')
    args = parser.parse_args()
    session = authenticate(args.username, args.password)
    get_folders(session)
    download_files(session)
    print("All files have been retrieved")

