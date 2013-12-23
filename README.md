# django-storage-swift: a storage layer for OpenStack Swift

django-storage-swift allows Django applications to use OpenStack Swift as a file storage layer.

## Features

+ Reads/writes files into/out of Swift.
+ Automatically derives the correct URL to allow files to be accessed through a web browser based on information returned from the authorisation server.
    + Allows you to override the host, port and path as necessary.


## Installing

To get started with django-storage-swift, install it through pip, then in your ```settings.py``` file, add:

```python
DEFAULT_FILE_STORAGE='swift.storage.SwiftStorage'
```

## Configuring

django-storage-swift recognises the following options.

| Option | Default | Description |
| ------ | ------- | ----------- |
| ```SWIFT_AUTH_URL``` | None | The URL for the auth server, e.g. ```http://127.0.0.1:5000/v2.0``` |
| ```SWIFT_USERNAME``` | None | The username to use to authenticate. |
| ```SWIFT_KEY``` | None | The key (password) to use to authenticate. |
| ```SWIFT_AUTH_VERSION``` | 1 | The version of the authentication protocol to use. |
| ```SWIFT_TENANT_NAME``` | None | The tenant name to use when authenticating. |
| ```SWIFT_CONTAINER_NAME``` | None | The container in which to store the files. |
| ```SWIFT_AUTO_CREATE_CONTAINER``` | False | Should the container be created if it does not exist? |
| ```SWIFT_BASE_URL``` | None | The base URL from which the files can be retrieved, e.g. ```http://127.0.0.1:8080/```.  |

### SWIFT_BASE_URL
django-swift-storage will automatically query the authentication server for the URL where your files can be accessed, which takes the form ```http://server:port/v1/AUTH_token/```.

Sometimes you want to override the server and port (for example if you're developing using [devstack][devstack] inside Vagrant). This can be accomplished with ```SWIFT_BASE_URL```.

The provided value is parsed, and:

 + host and port override any automatically derived values
 + any path component is put before derived path components.

So if your auth server returns ```http://10.0.2.2:8080/v1/AUTH_012345abcd/``` and you have ```SWIFT_BASE_URL="http://127.0.0.1:8888/foo"```, the ```url``` function will a path based on ```http://127.0.0.1:8888/foo/v1/AUTH_012345abcd/```.

## Use
Once installed and configured, use of django-storage-swift should be automatic and seamless.

You can verify that swift is indeed being used by running, inside ```python manage.py shell```:

```python
from django.core.files.storage import default_storage
default_storage.connection
```

The result should be ```<<swiftclient.client.Connection object ...>>```

## Troubleshooting

+ **I'm getting permission errors accessing my files**: You may need to make the container publically readable. See [this helpful discussion][public-container-help].

[devstack]: http://devstack.org/
[public-container-help]: http://support.rc.nectar.org.au/forum/viewtopic.php?f=6&t=272
