# django-storage-swift: a storage layer for OpenStack Swift

django-storage-swift allows Django applications to use OpenStack Swift as a file storage layer.

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
| ```SWIFT_BASE_URL``` | None | The base URL from which the files can be retrieved, e.g. ```http://127.0.0.1:8080/v1/AUTH_your_auth/your_container_name``` |

## Use
Once installed and configured, use of django-storage-swift should be automatic and seamless.

You can verify that swift is indeed being used by running, inside ```python manage.py shell```:

```python
from django.core.files.storage import default_storage
default_storage.connection
```

The result should be ```<<swiftclient.client.Connection object ...>>```
