#!/usr/bin/env python3

import argparse
import auckland_auth
import util


parser = argparse.ArgumentParser(description='Download lecture recordings from University of Auckland')
parser.add_argument('username')
parser.add_argument('password')
parser.add_argument('url', help='url to the recording to download')
args = parser.parse_args()
session = auckland_auth.authenticate(args.url, args.username, args.password)
util.download(session, args.url)
