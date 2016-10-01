import requests
import re
import os
from http.cookiejar import LWPCookieJar
from urllib.parse import urlparse

certs_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cert_bundle")

def authenticate(url, username, pasword):
    """Use the username and password to authenticate to auckland university, and return
    a requests session object with all needed cookies
    """
    # TODO check http response code for each request
    # Try to load existing session from disk
    cookie_file = "." + urlparse(url).hostname + "_cookiejar"
    session = get_cookies(cookie_file)
    if session:
        # Check if cookies are valid
        r = session.head(url, verify=certs_file)
        if r.status_code == 200:
            print("Cookies from %s are ok" % cookie_file)
            return session
    # Create session
    session = requests.Session()
    session.cookies = LWPCookieJar(cookie_file)
    # Make initial request to canvas
    response = session.get(url, allow_redirects=True, verify=certs_file)
    # Send credentials
    form_data = {
        'j_username': username,
        'j_password': pasword,
        '_eventId_proceed': ''
    }
    response = session.post("https://iam.auckland.ac.nz/profile/SAML2/Redirect/SSO?execution=e1s1", data=form_data, allow_redirects=True, verify=certs_file)
    # Need to parse SamlResponse from response body
    pattern = re.compile('(<input type="hidden" name="SAMLResponse" value=")(.*)(")')
    match = pattern.search(response.text)
    SAMLResponse = match.group(2)
    # Send SamlResponse
    form_data = {
        'SAMLResponse' : SAMLResponse
    }
    # Extract next location from form
    pattern = re.compile('(<form action=")(.*)(" method="post">)')
    match = pattern.search(response.text)
    SAML_post_location = match.group(2)
    SAML_post_location = SAML_post_location.replace('&#x2f;', '/')
    SAML_post_location = SAML_post_location.replace('&#x3a;', ':')
    # Post SamlResponse
    response = session.post(SAML_post_location, data=form_data, allow_redirects=True, verify=certs_file)
    # Save the cookies to disk
    session.cookies.save(ignore_discard=True)
    return session

def get_cookies(cookie_file):
    """Retrieve cookie jar from disk if it exists and return a session containing it, else return none"""
    session = requests.Session()
    session.cookies = LWPCookieJar(cookie_file)
    if os.path.exists(cookie_file):
        # Load cookies, including ones with the discard flag
        session.cookies.load(ignore_discard=True)
        return session
    else:
        return None

