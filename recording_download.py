#!/usr/bin/env python3

import argparse
import auckland_auth
import util


parser = argparse.ArgumentParser(description='Download lecture recordings from University of Auckland')
parser.add_argument('username')
parser.add_argument('password')
parser.add_argument('url', help='url to the recording to download')
parser.add_argument('--filename', dest='filename', help='name to save download as', nargs=1, default=None)
args = parser.parse_args()
session = auckland_auth.authenticate(args.url, args.username, args.password)
util.download(session, args.url, filename=args.filename[0])
