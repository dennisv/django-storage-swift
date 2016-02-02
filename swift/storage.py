import hmac
import mimetypes
import os
import re
from datetime import datetime
from hashlib import sha1
from io import BytesIO
from time import time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files import File
from django.core.files.storage import Storage
from six import b
from six.moves.urllib import parse as urlparse

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
    tenant_id = setting('SWIFT_TENANT_ID')
    user_domain_name = setting('SWIFT_USER_DOMAIN_NAME')
    user_domain_id = setting('SWIFT_USER_DOMAIN_ID')
    project_domain_name = setting('SWIFT_PROJECT_DOMAIN_NAME')
    project_domain_id = setting('SWIFT_PROJECT_DOMAIN_ID')
    container_name = setting('SWIFT_CONTAINER_NAME')
    auto_create_container = setting('SWIFT_AUTO_CREATE_CONTAINER', False)
    auto_create_container_public = setting(
        'SWIFT_AUTO_CREATE_CONTAINER_PUBLIC', False)
    auto_create_container_allow_orgin = setting(
        'SWIFT_AUTO_CREATE_CONTAINER_ALLOW_ORIGIN', None)
    auto_base_url = setting('SWIFT_AUTO_BASE_URL', True)
    override_base_url = setting('SWIFT_BASE_URL')
    use_temp_urls = setting('SWIFT_USE_TEMP_URLS', False)
    temp_url_key = setting('SWIFT_TEMP_URL_KEY')
    temp_url_duration = setting('SWIFT_TEMP_URL_DURATION', 30 * 60)
    auth_token_duration = setting('SWIFT_AUTH_TOKEN_DURATION', 60 * 60 * 23)
    os_extra_options = setting('SWIFT_EXTRA_OPTIONS', {})
    auto_overwrite = setting('SWIFT_AUTO_OVERWRITE', False)
    _token_creation_time = 0
    _token = ''
    name_prefix = setting('SWIFT_NAME_PREFIX')

    def __init__(self, **settings):
        # check if some of the settings provided as class attributes
        # should be overwritten
        for name, value in settings.items():
            if hasattr(self, name):
                setattr(self, name, value)

        self.last_headers_name = None
        self.last_headers_value = None

        os_options = {
            'tenant_id': self.tenant_id,
            'tenant_name': self.tenant_name,
            'user_domain_id': self.user_domain_id,
            'user_domain_name': self.user_domain_name,
            'project_domain_id': self.project_domain_id,
            'project_domain_name': self.project_domain_name
        }
        os_options.update(self.os_extra_options)

        # Get authentication token
        self.storage_url, self.token = swiftclient.get_auth(
            self.api_auth_url,
            self.api_username,
            self.api_key,
            auth_version=self.auth_version,
            os_options=os_options)
        self.http_conn = swiftclient.http_connection(self.storage_url)

        # Check container
        try:
            swiftclient.head_container(self.storage_url,
                                       self.token,
                                       self.container_name,
                                       http_conn=self.http_conn)
        except swiftclient.ClientException:
            headers = {}
            if self.auto_create_container:
                if self.auto_create_container_public:
                    headers['X-Container-Read'] = '.r:*'
                if self.auto_create_container_allow_orgin:
                    headers['X-Container-Meta-Access-Control-Allow-Origin'] = \
                        self.auto_create_container_allow_orgin
                swiftclient.put_container(self.storage_url,
                                          self.token,
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
                split_derived = urlparse.urlsplit(self.base_url)
                split_override = urlparse.urlsplit(self.override_base_url)
                split_result = [''] * 5
                split_result[0:2] = split_override[0:2]
                split_result[2] = (split_override[2] + split_derived[2]
                                   ).replace('//', '/')
                self.base_url = urlparse.urlunsplit(split_result)

            self.base_url = urlparse.urljoin(self.base_url,
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
                os_options={"tenant_name": self.tenant_name})[1]
            self.token = new_token
        return self._token

    def set_token(self, new_token):
        self._token_creation_time = time()
        self._token = new_token

    token = property(get_token, set_token)

    def _open(self, name, mode='rb'):
        if self.name_prefix:
            name = self.name_prefix + name

        headers, content = swiftclient.get_object(self.storage_url,
                                                  self.token,
                                                  self.container_name,
                                                  name,
                                                  http_conn=self.http_conn)
        buf = BytesIO(content)
        buf.name = os.path.basename(name)
        buf.mode = mode
        return File(buf)

    def _save(self, name, content):
        if self.name_prefix:
            name = self.name_prefix + name

        content_type = mimetypes.guess_type(name)[0]
        swiftclient.put_object(self.storage_url,
                               self.token,
                               self.container_name,
                               name,
                               content,
                               http_conn=self.http_conn,
                               content_type=content_type)
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
                self.storage_url,
                self.token,
                self.container_name,
                name,
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
            swiftclient.delete_object(self.storage_url,
                                      self.token,
                                      self.container_name,
                                      name,
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

        if not self.auto_overwrite:
            name = super(SwiftStorage, self).get_available_name(name)

        return name

    def size(self, name):
        return int(self.get_headers(name)['content-length'])

    def modified_time(self, name):
        return datetime.fromtimestamp(
            float(self.get_headers(name)['x-timestamp']))

    def url(self, name):
        return self._path(name)

    def _path(self, name):
        name = self.name_prefix + name
        url = urlparse.urljoin(self.base_url, name)

        # Are we building a temporary url?
        if self.use_temp_urls:
            expires = int(time() + int(self.temp_url_duration))
            method = 'GET'
            path = urlparse.urlsplit(url).path
            sig = hmac.new(b(self.temp_url_key), b('%s\n%s\n%s' %
                                                   (method, expires, path)),
                           sha1).hexdigest()
            url = url + '?temp_url_sig=%s&temp_url_expires=%s' % (sig, expires)

        return url

    def path(self, name):
        raise NotImplementedError

    def isdir(self, name):
        return '.' not in name

    def listdir(self, path):
        container = swiftclient.get_container(self.storage_url, self.token,
                                              self.container_name)
        files = []
        dirs = []
        path = self.name_prefix + path
        for obj in container[1]:
            if not obj['name'].startswith(path):
                continue

            path = obj['name'][len(path):].split('/')
            key = path[0] if path[0] else path[1]

            if not self.isdir(key):
                files.append(key)
            elif key not in dirs:
                dirs.append(key)

        return dirs, files

    def makedirs(self, dirs):
        swiftclient.put_object(self.storage_url,
                               token=self.token,
                               container=self.container_name,
                               name='%s/.' % dirs,
                               contents='')

    def rmtree(self, abs_path):
        container = swiftclient.get_container(self.storage_url, self.token,
                                              self.container_name)

        for obj in container[1]:
            if obj['name'].startswith(abs_path):
                swiftclient.delete_object(self.storage_url,
                                          token=self.token,
                                          container=self.container_name,
                                          name=obj['name'])


class StaticSwiftStorage(SwiftStorage):
    container_name = setting('SWIFT_STATIC_CONTAINER_NAME')
    name_prefix = setting('SWIFT_STATIC_NAME_PREFIX')
    override_base_url = setting('SWIFT_STATIC_BASE_URL')

    def get_available_name(self, name):
        """
        When running collectstatic we don't want to return an available name,
        we want to return the same name because if the file exists we want to
        overwrite it.
        """
        return name
