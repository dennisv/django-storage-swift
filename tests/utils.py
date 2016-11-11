
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


def base_url(container_name=None):
    if container_name:
        return "{}/{}/".format(base_url(), container_name)
    return "{}/AUTH_{}".format(BASE_URL, TENANT_ID)


class FakeSwift(object):
    ClientException = None

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
    def get_container(cls, *args, **kwargs):
        pass


class FakeHttpConn(object):
    pass

