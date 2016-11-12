from copy import deepcopy

BASE_URL = 'https://objects.example.com/v1'
AUTH_URL = 'https://auth.example.com'
TENANT_ID = '11223344556677889900aabbccddeeff'
TOKEN = 'auth_token'

AUTH_PARAMETERS = {
    'v1': {
        'api_auth_url': 'https://objects.example.com',
        'api_username': 'user',
        'api_key': 'auth_key',
    },
    'v2': {
        'api_auth_url': 'https://objects.example.com',
        'api_username': 'user',
        'api_key': 'auth_key',
        'tenant_name': 'tenant'
    },
    'v3': {
        'api_auth_url': 'https://objects.example.com',
        'api_username': 'user',
        'api_key': 'auth_key',
        'user_domain_name': 'domain',
        'project_domain_name': 'domain',
        'tenant_name': 'project',
    }
}


def auth_params(version, **kwargs):
    """Appends auth parameters"""
    kwargs.update(AUTH_PARAMETERS[version])
    return kwargs


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
        return "{}/{}/{}".format(base_url(), container, path or '')
    return "{}/AUTH_{}".format(BASE_URL, TENANT_ID)


class ClientException(Exception):
    pass


class FakeSwift(object):
    ClientException = ClientException
    objects = CONTAINER_CONTENTS

    @classmethod
    def get_auth(cls, auth_url, user, passwd, **kwargs):
        return base_url(), TOKEN

    @classmethod
    def http_connection(cls, *args, **kwargs):
        return FakeHttpConn()

    @classmethod
    def head_container(cls, *args, **kwargs):
        pass

    @classmethod
    def head_object(cls, url, token, container, name, **kwargs):
        for obj in FakeSwift.objects:
            if obj['name'] == name:
                object = deepcopy(obj)
                object['content-length'] = obj['bytes']
                return object
        raise FakeSwift.ClientException

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

    @classmethod
    def put_object(cls, url, name=None, token=None, container=None, contents=None):
        if not name:
            raise ValueError("Attempting to add an object with no name/path")
        FakeSwift.objects.append(create_object(name))


class FakeHttpConn(object):
    pass
