from StringIO import StringIO
import re
import os
import urlparse

from django.core.files import File
from django.core.files.storage import Storage
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

try:
    import swiftclient
except ImportError:
    raise ImproperlyConfigured("Could not load swiftclient library")


def setting(name, default=None):
    return getattr(settings, name, default)


class SwiftStorage(Storage):
    api_auth_url = setting('SWIFT_AUTH_URL')
    api_username = setting('SWIFT_USERNAME')
    api_key = setting('SWIFT_KEY')
    auth_version = setting('SWIFT_AUTH_VERSION', 1)
    tenant_name = setting('SWIFT_TENANT_NAME')
    container_name = setting('SWIFT_CONTAINER_NAME')
    auto_create_container = setting('SWIFT_AUTO_CREATE_CONTAINER', False)
    base_url = setting('SWIFT_BASE_URL')

    def __init__(self):
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = swiftclient.Connection(
                authurl=self.api_auth_url,
                auth_version=self.auth_version,
                user=self.api_username,
                key=self.api_key,
                tenant_name=self.tenant_name)

        try:
            self._connection.head_container(self.container_name)
        except swiftclient.ClientException:
            if self.auto_create_container:
                self._connection.put_container(self.container_name)
            else:
                raise ImproperlyConfigured("Container %s does not exist."
                                           % self.container_name)

        return self._connection

    def _open(self, name, mode='rb'):
        headers, content = self.connection.get_object(self.container_name,
                                                      name)
        buf = StringIO(content)
        buf.name = os.path.basename(name)
        buf.mode = mode
        return File(buf)

    def _save(self, name, content):
        self.connection.put_object(self.container_name, name, content)
        return name

    def exists(self, name):
        try:
            self.connection.head_object(self.container_name, name)
        except swiftclient.ClientException:
            return False
        return True

    def delete(self, name):
        try:
            self.connection.delete_object(self.container_name, name)
        except swiftclient.ClientException:
            pass

    def get_valid_name(self, name):
        s = name.strip().replace(' ', '_')
        return re.sub(r'(?u)[^-_\w./]', '', s)

    def size(self, name):
        headers, content = self.connection.get_object(self.container_name,
                                                      name)
        return len(content)

    def url(self, name):
        return urlparse.urljoin(self.base_url, name).replace('\\', '/')
