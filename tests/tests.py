from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
from mock import patch
from .utils import FakeSwift, auth_params
from swift import storage


@patch('swift.storage.swiftclient', new=FakeSwift)
class AuthTest(TestCase):

    def test_instantiate_default(self):
        """Instantiate default backend with no parameters"""
        with self.assertRaises(ImproperlyConfigured):
            storage.SwiftStorage()

    def test_instantiate_static(self):
        """Instantiate static backend with no parameters"""
        with self.assertRaises(ImproperlyConfigured):
            storage.StaticSwiftStorage()

    def test_auth_v1(self):
        """Test version 1 authentication"""
        storage.SwiftStorage(**auth_params('v1', container_name="data"))

    def test_auth_v2(self):
        """Test version 2 authentication"""
        storage.SwiftStorage(**auth_params('v2', container_name="data"))

    def test_auth_v3(self):
        """Test version 3 authentication"""
        storage.SwiftStorage(**auth_params('v3', container_name="data"))

    def test_auth_v1_detect_version(self):
        """Test version 1 authentication detection"""
        backend = storage.SwiftStorage(**auth_params('v1', container_name="data"))
        self.assertEqual(backend.auth_version, '1')

    def test_auth_v2_detect_version(self):
        """Test version 2 authentication detection"""
        backend = storage.SwiftStorage(**auth_params('v2', container_name="data"))
        self.assertEqual(backend.auth_version, '2')

    def test_auth_v3_detect_version(self):
        """Test version 3 authentication detection"""
        backend = storage.SwiftStorage(**auth_params('v3', container_name="data"))
        self.assertEqual(backend.auth_version, '3')



# @patch('swift.storage.swiftclient', new=FakeSwift)
# class BackendTest(TestCase):
#
#     def test_listdir(self):
#         backend = storage.SwiftStorage(**auth_params('v2', container_name="data"))
#         backend.listdir('/')
