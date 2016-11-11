from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
from mock import patch
from .utils import FakeSwift, auth_params, base_url
from swift import storage


class SwiftStorageTestCase(TestCase):

    def default_storage(self, auth_version, **params):
        """Instantiate default storage with auth parameters"""
        return storage.SwiftStorage(**auth_params(auth_version, **params))

    def static_storage(self, auth_version, **params):
        """Instantiate static storage with auth parameters"""
        return storage.StaticSwiftStorage(**auth_params(auth_version, **params))


@patch('swift.storage.swiftclient', new=FakeSwift)
class AuthTest(SwiftStorageTestCase):
    """Test authentication parameters"""

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
        self.default_storage('v1', container_name="data")

    def test_auth_v2(self):
        """Test version 2 authentication"""
        self.default_storage('v2', container_name="data")

    def test_auth_v3(self):
        """Test version 3 authentication"""
        self.default_storage('v3', container_name="data")

    def test_auth_v1_detect_version(self):
        """Test version 1 authentication detection"""
        backend = self.default_storage('v1', container_name="data")
        self.assertEqual(backend.auth_version, '1')

    def test_auth_v2_detect_version(self):
        """Test version 2 authentication detection"""
        backend = self.default_storage('v2', container_name="data")
        self.assertEqual(backend.auth_version, '2')

    def test_auth_v3_detect_version(self):
        """Test version 3 authentication detection"""
        backend = self.default_storage('v3', container_name="data")
        self.assertEqual(backend.auth_version, '3')


@patch('swift.storage.swiftclient', new=FakeSwift)
class ConfigTest(SwiftStorageTestCase):

    def test_auto_base_url(self):
        """Automatically resolve base url"""
        container_name = "data"
        backend = self.default_storage('v3', container_name=container_name, auto_base_url=True)
        self.assertEqual(backend.base_url, base_url(container_name=container_name))

    def test_override_base_url_no_auto(self):
        """Test overriding base url without auto base url"""
        url = 'http://localhost:8080/test/'
        backend = self.default_storage('v3',
                                       container_name="data",
                                       auto_base_url=False,
                                       override_base_url=url)
        self.assertEqual(backend.base_url, url)

    # NOTE: How is this supposed to work?
    # Should we be able to use base_url override with auto_base_url?
    # This is currently possible in the code
    # ---
    # def test_override_base_url_auto(self):
    #     """Test overriding base url with auto"""
    #     url = 'http://localhost:8080/test/'
    #     backend = self.default_storage('v3',
    #                                    container_name="data",
    #                                    auto_base_url=True,
    #                                    override_base_url=url)
    #     self.assertEqual(backend.base_url, url)


# @patch('swift.storage.swiftclient', new=FakeSwift)
# class BackendTest(TestCase):
#
#     def test_listdir(self):
#         backend = storage.SwiftStorage(**auth_params('v2', container_name="data"))
#         backend.listdir('/')
