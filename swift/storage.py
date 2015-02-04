from io import StringIO
import re
import os
import posixpath
import urllib.parse
import hmac
import itertools
from hashlib import sha1
from time import time
from datetime import datetime

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
    auto_create_container_public = setting(
        'SWIFT_AUTO_CREATE_CONTAINER_PUBLIC', False)
    auto_base_url = setting('SWIFT_AUTO_BASE_URL', True)
    override_base_url = setting('SWIFT_BASE_URL')
    use_temp_urls = setting('SWIFT_USE_TEMP_URLS', False)
    temp_url_key = setting('SWIFT_TEMP_URL_KEY')
    temp_url_duration = setting('SWIFT_TEMP_URL_DURATION', 30*60)
    auth_token_duration = setting('SWIFT_AUTH_TOKEN_DURATION', 60*60*23)
    os_extra_options = setting('SWIFT_EXTRA_OPTIONS', {})
    _token_creation_time = 0
    _token = ''
    name_prefix = setting('SWIFT_NAME_PREFIX')

    def __init__(self):
        self.last_headers_name = None
        self.last_headers_value = None

        # Get authentication token
        self.storage_url, self.token = swiftclient.get_auth(
            self.api_auth_url,
            self.api_username,
            self.api_key,
            auth_version=self.auth_version,
            os_options=dict(list({"tenant_name": self.tenant_name}.items()) +
                            list(self.os_extra_options.items())),
        )
        self.http_conn = swiftclient.http_connection(self.storage_url)

        # Check container
        try:
            swiftclient.head_container(self.storage_url, self.token,
                                       self.container_name,
                                       http_conn=self.http_conn)
        except swiftclient.ClientException:
            headers = {}
            if self.auto_create_container:
                if self.auto_create_container_public:
                    headers['X-Container-Read'] = '.r:*'
                swiftclient.put_container(self.storage_url, self.token,
                                          self.container_name,
                                          http_conn=self.http_conn,
                                          headers=headers)
            else:
                raise ImproperlyConfigured(
                    "Container %s does not exist." % self.container_name)

        if self.auto_base_url:
            # Derive a base URL based on the authentication information from
            # the server, optionally overriding the protocol, host/port and
            # potentially adding a path fragment before the auth information.
            self.base_url = self.storage_url + '/'
            if self.override_base_url is not None:
                # override the protocol and host, append any path fragments
                split_derived = urllib.parse.urlsplit(self.base_url)
                split_override = urllib.parse.urlsplit(self.override_base_url)
                split_result = [''] * 5
                split_result[0:2] = split_override[0:2]
                split_result[2] = (split_override[2] +
                                   split_derived[2]).replace('//', '/')
                self.base_url = urllib.parse.urlunsplit(split_result)

            self.base_url = urllib.parse.urljoin(self.base_url,
                                             self.container_name)
            self.base_url += '/'
        else:
            self.base_url = self.override_base_url

    def get_token(self):
        if time() - self._token_creation_time >= self.auth_token_duration:
            new_token = swiftclient.get_auth(
                self.api_auth_url,
                self.api_username,
                self.api_key,
                auth_version=self.auth_version,
                os_options={"tenant_name": self.tenant_name},
            )[1]
            self.token = new_token
        return self._token

    def set_token(self, new_token):
        self._token_creation_time = time()
        self._token = new_token

    token = property(get_token, set_token)

    def _open(self, name, mode='rb'):
        if self.name_prefix:
            name = self.name_prefix + name

        headers, content = swiftclient.get_object(self.storage_url, self.token,
                                                  self.container_name, name,
                                                  http_conn=self.http_conn)
        buf = StringIO(content)
        buf.name = os.path.basename(name)
        buf.mode = mode
        return File(buf)

    def _save(self, name, content):
        if self.name_prefix:
            name = self.name_prefix + name

        swiftclient.put_object(self.storage_url, self.token,
                               self.container_name, name, content,
                               http_conn=self.http_conn)
        return name

    def get_headers(self, name):
        """
        Optimization : only fetch headers once when several calls are made
        requiring information for the same name.
        When the caller is collectstatic, this makes a huge difference.
        According to my test, we get a *2 speed up. Which makes sense : two
        api calls were made..
        """
        if self.name_prefix:
            name = self.name_prefix + name

        if name != self.last_headers_name:
            # miss -> update
            self.last_headers_value = swiftclient.head_object(
                self.storage_url, self.token, self.container_name, name,
                http_conn=self.http_conn)
            self.last_headers_name = name
        return self.last_headers_value

    def exists(self, name):
        try:
            self.get_headers(name)
        except swiftclient.ClientException:
            return False
        return True

    def delete(self, name):
        try:
            swiftclient.delete_object(self.storage_url, self.token,
                                      self.container_name, name,
                                      http_conn=self.http_conn)
        except swiftclient.ClientException:
            pass

    def get_valid_name(self, name):
        s = name.strip().replace(' ', '_')
        return re.sub(r'(?u)[^-_\w./]', '', s)

    def get_available_name(self, name):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        # If the filename already exists, add an underscore and a number
        # (before the file extension, if one exists) to the filename until the
        # generated filename doesn't exist.
        count = itertools.count(1)
        while self.exists(name):
            # file_ext includes the dot.
            name = posixpath.join(dir_name, "%s_%s%s" % (file_root,
                                                         next(count),
                                                         file_ext))

        return name

    def size(self, name):
        return int(self.get_headers(name)['content-length'])

    def modified_time(self, name):
        return datetime.fromtimestamp(
            float(self.get_headers(name)['x-timestamp']))

    def url(self, name):
        return self._path(name)

    def _path(self, name):
        url = urllib.parse.urljoin(self.base_url, name)

        # Are we building a temporary url?
        if self.use_temp_urls:
            expires = int(time() + int(self.temp_url_duration))
            method = 'GET'
            path = urllib.parse.urlsplit(url).path
            sig = hmac.new(self.temp_url_key,
                           '%s\n%s\n%s' % (method, expires, path),
                           sha1).hexdigest()
            url = url + '?temp_url_sig=%s&temp_url_expires=%s' % (sig, expires)

        return url

    def path(self, name):
        raise NotImplementedError


class StaticSwiftStorage(SwiftStorage):
    container_name = setting('SWIFT_STATIC_CONTAINER_NAME')
    name_prefix = setting('SWIFT_STATIC_NAME_PREFIX')
    override_base_url = setting('SWIFT_STATIC_BASE_URL')
