from copy import deepcopy
from six.moves.urllib import parse as urlparse

BASE_URL = 'https://objects.example.com/v1'
AUTH_URL = 'https://auth.example.com'
TENANT_ID = '11223344556677889900aabbccddeeff'
TOKEN = 'auth_token'

AUTH_PARAMETERS = {
    'v1': {
        'api_auth_url': 'https://objects.example.com',
        'api_username': 'user',
        'api_key': 'auth_key',
        'auth_version': '1',
        'container_name': "container",
    },
    'v2': {
        'api_auth_url': 'https://objects.example.com',
        'api_username': 'user',
        'api_key': 'auth_key',
        'tenant_name': 'tenant',
        'tenant_id': 'tenant',
        'auth_version': '2',
        'container_name': "container"
    },
    'v3': {
        'api_auth_url': 'https://objects.example.com',
        'api_username': 'user',
        'api_key': 'auth_key',
        'auth_version': '3',
        'user_domain_name': 'domain',
        'user_domain_id': 'domain',
        'project_domain_name': 'domain',
        'project_domain_id': 'domain',
        'tenant_name': 'project',
        'container_name': "container"
    }
}


def auth_params(auth_config, exclude=None, **kwargs):
    """Appends auth parameters"""
    params = deepcopy(AUTH_PARAMETERS[auth_config])
    if exclude:
        for name in exclude:
            del params[name]
    params.update(kwargs)
    return params


def create_object(path, content_type='image/png', bytes=4096,
                  hash='fcfc6539ce4e545ce58bafeeac3303a7',
                  last_modified='2016-08-27T23:12:22.993170'):
    """Creates a fake swift object"""
    return {
        'hash': hash,
        'last_modified': last_modified,
        'name': path,
        'content_type': content_type,
        'bytes': bytes,
    }

# Files stored in the backend by default
CONTAINER_FILES = [
    'root.txt',
    'images/test.png',
    'css/test.css',
    'js/test.js',
]

CONTAINER_CONTENTS = [create_object(path) for path in CONTAINER_FILES]


def base_url(container=None, path=None):
    if container:
        try:
            path = urlparse.quote(path.encode('utf-8'))
        except (UnicodeDecodeError, AttributeError):
            pass
        return "{}/{}/{}".format(base_url(), container, path or '')
    return "{}/AUTH_{}".format(BASE_URL, TENANT_ID)


class ClientException(Exception):
    pass


class FakeSwift(object):
    ClientException = ClientException
    objects = CONTAINER_CONTENTS
    containers = ['container']

    class Connection(object):
        service_token = None
        def __init__(self, authurl=None, user=None, key=None, retries=5,
                     preauthurl=None, preauthtoken=None, snet=False,
                     starting_backoff=1, max_backoff=64, tenant_name=None,
                     os_options=None, auth_version="1", cacert=None,
                     insecure=False, cert=None, cert_key=None,
                     ssl_compression=True, retry_on_ratelimit=False,
                     timeout=None, session=None):
            pass

        def _retry(self, reset_func, func, *args, **kwargs):
            self.url, self.token = self.get_auth()
            self.http_conn = None
            return func(self.url, self.token, *args,
                        service_token=self.service_token, **kwargs)

        def get_auth(self):
            return base_url(), TOKEN

        def head_container(self, container, headers=None):
            return self._retry(None, FakeSwift.head_container, container,
                               headers=headers)

        def put_container(self, container, headers=None, response_dict=None,
                          query_string=None):
            return self._retry(None, FakeSwift.put_container, container,
                               headers=headers, response_dict=response_dict,
                               query_string=query_string)

        def head_object(self, container, obj, headers=None):
            return self._retry(None, FakeSwift.head_object, container, obj,
                               headers=headers)

        def get_object(self, container, obj, resp_chunk_size=None,
                       query_string=None, response_dict=None, headers=None):
            return self._retry(None, FakeSwift.get_object, container, obj,
                               resp_chunk_size=resp_chunk_size,
                               query_string=query_string,
                               response_dict=response_dict, headers=headers)

        def get_container(self, container, marker=None, limit=None, prefix=None,
                          delimiter=None, end_marker=None, path=None,
                          full_listing=False, headers=None, query_string=None):
            return self._retry(None, FakeSwift.get_container, container,
                               marker=marker, limit=limit, prefix=prefix,
                               delimiter=delimiter, end_marker=end_marker,
                               path=path, full_listing=full_listing,
                               headers=headers, query_string=query_string)

        def delete_object(self, container, obj, query_string=None,
                          response_dict=None, headers=None):
            return self._retry(None, FakeSwift.delete_object, container, obj,
                               query_string=query_string,
                               response_dict=response_dict, headers=headers)

        def put_object(self, container, obj, contents, content_length=None,
                       etag=None, chunk_size=None, content_type=None,
                       headers=None, query_string=None, response_dict=None):
            return self._retry(None, FakeSwift.put_object, container, obj,
                               contents, content_length=content_length,
                               etag=etag, chunk_size=chunk_size,
                               content_type=content_type, headers=headers,
                               query_string=query_string,
                               response_dict=response_dict)

    @classmethod
    def get_auth(cls, auth_url, user, passwd, **kwargs):
        return base_url(), TOKEN

    @classmethod
    def http_connection(cls, *args, **kwargs):
        return FakeHttpConn()

    @classmethod
    def head_container(cls, url, token, container, **kwargs):
        if container not in FakeSwift.containers:
            raise ClientException

    @classmethod
    def put_container(cls, url, token, container, **kwargs):
        if container not in cls.containers:
            cls.containers.append(container)

    @classmethod
    def head_object(cls, url, token, container, name, **kwargs):
        for obj in FakeSwift.objects:
            if obj['name'] == name:
                object = deepcopy(obj)
                object['content-length'] = obj['bytes']
                object['x-timestamp'] = '123456789'
                return object
        raise FakeSwift.ClientException

    @classmethod
    def get_object(cls, url, token, container, name, **kwargs):
        return None, bytearray(4096)

    @classmethod
    def get_container(cls, storage_url, token, container, **kwargs):
        """Returns a tuple: Response headers, list of objects"""
        return None, FakeSwift.objects

    @classmethod
    def delete_object(cls, url, token, container, name, **kwargs):
        for obj in FakeSwift.objects:
            if obj['name'] == name:
                FakeSwift.objects.remove(obj)
                return
        raise cls.ClientException

    @classmethod
    def put_object(cls, url, token, container, name=None, contents=None,
                   http_conn=None, content_type=None, content_length=None,
                   headers=None, **kwargs):
        if not name:
            raise ValueError("Attempting to add an object with no name/path")
        FakeSwift.objects.append(create_object(name))


class FakeHttpConn(object):
    pass
