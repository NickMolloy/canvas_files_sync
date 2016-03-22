# University of Auckland File Synchronisation

###canvas_files_download.py
Provides the ability to download all files from User's Canvas files to local filesystem, maintaining the
same directory structure as on Canvas
#####Usage
```
canvas_files_download.py [-h] [--show-existing] username password
```
```
positional arguments:
  username         Canvas username  
  password         Canvas password

optional arguments:
  -h, --help       show help message and exit  
  --show-existing  List files found on Canvas even if they exist on disk
```

Currently, the files will be downloaded to the directory from which this is run.

<br>

###recording_download.py
Allows downloading lecture recordings from University of Auckland

#####Usage
```
recording_download.py [-h] username password url  
```
```
positional arguments:  
  username  
  password  
  url         url to the recording to download

optional arguments:  
  -h, --help  show this help message and exit
```

Currently, the files will be downloaded to the directory from which this is run.

<br>

###auckland_auth.py
Handles authentication to University of Auckland services

<br>

###util.py
Contains common functionality (only downloading at the moment)
