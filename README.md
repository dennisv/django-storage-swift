# django-storage-swift: a storage layer for OpenStack Swift

django-storage-swift allows Django applications to use OpenStack Swift as a file storage layer.

## Features

+ Reads/writes files into/out of Swift.
+ Automatically derives the correct URL to allow files to be accessed through a web browser based on information returned from the authorisation server.
    + Allows you to override the host, port and path as necessary.
    + Supports the generation of temporary URLs to restrict access to files.


## Usage

You can install django-storage-swift through pip.
To store your media files on swift, add the following line to your
settings.py or local\_settings.py:

```python
DEFAULT_FILE_STORAGE='swift.storage.SwiftStorage'
```

To store your static files on swift, add the following line:
```python
STATICFILES_STORAGE ='swift.storage.StaticSwiftStorage'
```
This will use another container.


## Configuring

django-storage-swift recognises the following options.

| Option | Default | Description |
| ------ | ------- | ----------- |
| ```SWIFT_AUTH_URL``` | None | The URL for the auth server, e.g. ```http://127.0.0.1:5000/v2.0``` |
| ```SWIFT_USERNAME``` | None | The username to use to authenticate. |
| ```SWIFT_KEY``` | None | The key (password) to use to authenticate. |
| ```SWIFT_AUTH_VERSION``` | 1 | The version of the authentication protocol to use. |
| ```SWIFT_TENANT_NAME``` | None | The tenant name to use when authenticating. |
| ```SWIFT_TENANT_ID``` | None | The tenant id to use when authenticating. |
| ```SWIFT_CONTAINER_NAME``` | None | The container in which to store the files. |
| ```SWIFT_STATIC_CONTAINER_NAME``` | None | Alternate container used by StaticSwiftStorage. |
| ```SWIFT_AUTO_CREATE_CONTAINER``` | False | Should the container be created if it does not exist? |
| ```SWIFT_AUTO_BASE_URL``` | True | Query the authentication server for the base URL. |
| ```SWIFT_BASE_URL``` | None | The base URL from which the files can be retrieved, e.g. ```http://127.0.0.1:8080/```.  |
| ```SWIFT_USE_TEMP_URLS``` | False | Generate temporary URLs for file access (allows files to be accessed without a permissive ACL). |
| ```SWIFT_TEMP_URL_KEY``` | None | Temporary URL key --- see [the OpenStack documentation][openstack-tempurl]. |
| ```SWIFT_TEMP_URL_DURATION``` | ```30*60``` | How long a temporary URL remains valid, in seconds. |
| ```SWIFT_EXTRA_OPTIONS``` | ```{}``` | Extra options, eg. { "endpoint_type": "adminURL"  }, which will return adminURL instead publicURL. | 

### SWIFT_BASE_URL
django-swift-storage will automatically query the authentication server for the URL where your files can be accessed, which takes the form ```http://server:port/v1/AUTH_token/```.

Sometimes you want to override the server and port (for example if you're developing using [devstack][devstack] inside Vagrant). This can be accomplished with ```SWIFT_BASE_URL```.

The provided value is parsed, and:

 + host and port override any automatically derived values
 + any path component is put before derived path components.

So if your auth server returns ```http://10.0.2.2:8080/v1/AUTH_012345abcd/``` and you have ```SWIFT_BASE_URL="http://127.0.0.1:8888/foo"```, the ```url``` function will a path based on ```http://127.0.0.1:8888/foo/v1/AUTH_012345abcd/```.

### Temporary URLs

Temporary URLs provide a means to grant a user permission to access a file for a limited time only and without making the entire container public.

Temporary URLs work as described in the Swift documentation. (The code to generate the signatures is heavily based on their implementation.) They require setup of a key for signing: the process is described in [the OpenStack documentation][openstack-tempurl].

## Use
Once installed and configured, use of django-storage-swift should be automatic and seamless.

You can verify that swift is indeed being used by running, inside ```python manage.py shell```:

```python
from django.core.files.storage import default_storage
default_storage.connection
```

The result should be ```<<swiftclient.client.Connection object ...>>```

## Troubleshooting

+ **I'm getting permission errors accessing my files**: If you are not using temporary URLs, you may need to make the container publically readable. See [this helpful discussion][public-container-help]. If you are using temporary URLs, verify that your key is set correctly.

[openstack-tempurl]: http://docs.openstack.org/trunk/config-reference/content//object-storage-tempurl.html
[devstack]: http://devstack.org/
[public-container-help]: http://support.rc.nectar.org.au/forum/viewtopic.php?f=6&t=272

## Quickstart

```
# This was executed on a VM running a SAIO, for example with
# https://github.com/swiftstack/vagrant-swift-all-in-one

# Create two world-readable containers
swift post -r ".r:*" django
swift post -r ".r:*" django-static

# A virtualenv to keep installation separated
virtualenv sampleenv
source sampleenv/bin/activate
pip install django-storage-swift
pip install django

# Create a sample project
django-admin startproject sampleproj
export DJANGO_SETTINGS_MODULE=sampleproj.settings
cd sampleproj/

# A few required settings, using SAIO defaults
cat <<EOF >> sampleproj/settings.py
DEFAULT_FILE_STORAGE='swift.storage.SwiftStorage'
STATICFILES_STORAGE ='swift.storage.StaticSwiftStorage'
SWIFT_AUTH_URL='http://127.0.0.1:8080/auth/v1.0'
SWIFT_USERNAME='test:tester'
SWIFT_KEY='testing'
SWIFT_CONTAINER_NAME='django'
SWIFT_STATIC_CONTAINER_NAME='django-static'
EOF

# Create the initial DB data
python manage.py migrate

# This uploads static files to Swift
python manage.py collectstatic --noinput

# Now open http://127.0.0.1:8000/admin/ in your browser
# Static files like CSS are served by Swift
python manage.py runserver
```
