from django.test import TestCase
from .utils import FakeSwift
from swift import storage


class DummyTestCase(TestCase):

    def setUp(self):
        storage.swiftclient = FakeSwift
        self.media_storage = storage.SwiftStorage()
        self.static_storage = storage.StaticSwiftStorage()

    def test_dummy(self):
        pass
