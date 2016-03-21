import urllib
import os
import sys

def download(session, url, output_location=None, verbose=False):
    """Download file at url, and save it to ouput_location"""
    # TODO, if file already exists on disk, check file length, and do something if it doesnt match http response
    if not output_location:
        # No output location given, so save file to current directory
        output_location = os.path.join(os.getcwd(), os.path.basename(url))
    filename = os.path.basename(output_location)
    # Check if file already exists on disk
    if os.path.exists(output_location):
        if verbose:
            print("%s already exists on disk" % output_location)
        return
    # Make needed directory
    os.makedirs(os.path.dirname(output_location), exist_ok=True)
    # Start download
    response = session.get(url, stream=True, verify=True)
    total_length = int(response.headers.get('content-length'))
    progress = 0
    print("Downloading: " + filename)
    try:
        with open(output_location, 'wb') as f:
            for chunk in response.iter_content(chunk_size=20480): 
                if chunk: # filter out keep-alive new chunks
                    progress += len(chunk)
                    f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())
                    done = int(50 * progress / total_length)
                    sys.stdout.write("\r[%s%s] %s" % ('=' * done, ' ' * (50-done), 'Progress: ' + str(done * 2) + '%') )    
                    sys.stdout.flush()
        print(" Done")
    except:
        print(" Failed")

