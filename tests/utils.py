
BASE_URL = 'https://objects.example.com'
TOKEN = 'token'


class FakeSwift(object):
    ClientException = None

    @classmethod
    def get_auth(cls, *args, **kwargs):
        return BASE_URL, TOKEN

    @classmethod
    def http_connection(cls, *args, **kwargs):
        return FakeHttpConn()


    @classmethod
    def head_container(cls, *args, **kwargs):
        pass

class FakeHttpConn(object):
    pass