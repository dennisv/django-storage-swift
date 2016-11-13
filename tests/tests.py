from copy import deepcopy
from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
from mock import patch
from .utils import FakeSwift, auth_params, base_url, CONTAINER_CONTENTS
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
        self.assertEqual(backend.base_url, base_url(container=container_name))

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


@patch('swift.storage.swiftclient', new=FakeSwift)
class BackendTest(SwiftStorageTestCase):

    @patch('swift.storage.swiftclient', new=FakeSwift)
    def setUp(self):
        self.backend = self.default_storage('v3', container_name="data")

    def test_url(self):
        """Get url for a resource"""
        name = 'images/test.png'
        url = self.backend.url(name)
        self.assertEqual(url, base_url(container=self.backend.container_name, path=name))

    def test_object_size(self):
        """Test getting object size"""
        size = self.backend.size('images/test.png')
        self.assertEqual(size, 4096)

    def test_object_exists(self):
        """Test for the existence of an object"""
        exists = self.backend.exists('images/test.png')
        self.assertTrue(exists)

    def test_object_dont_exists(self):
        """Test for the existence of an non-existent object"""
        exists = self.backend.exists('warez/some_random_movie.mp4')
        self.assertFalse(exists)

    def test_listdir(self):
        """List root in container"""
        dirs, files = self.backend.listdir('')
        self.assertListEqual(dirs, ['images', 'css', 'js'])
        self.assertListEqual(files, ['root.txt'])

    @patch('tests.utils.FakeSwift.objects', new=deepcopy(CONTAINER_CONTENTS))
    def test_rmtree(self):
        """Remove folder in storage"""
        backend = self.default_storage('v3', container_name="data")
        backend.rmtree('images')
        dirs, files = self.backend.listdir('')
        self.assertListEqual(dirs, ['css', 'js'])
        self.assertListEqual(files, ['root.txt'])

    @patch('tests.utils.FakeSwift.objects', new=deepcopy(CONTAINER_CONTENTS))
    def test_mkdirs(self):
        """Make directory/pseudofolder in backend"""
        backend = self.default_storage('v3', container_name="data")
        backend.makedirs('downloads')
        dirs, files = self.backend.listdir('')
        self.assertListEqual(dirs, ['images', 'css', 'js', 'downloads'])
        self.assertListEqual(files, ['root.txt'])

    @patch('tests.utils.FakeSwift.objects', new=deepcopy(CONTAINER_CONTENTS))
    def test_delete_object(self):
        """Delete an object"""
        backend = self.default_storage('v3', container_name="data")
        backend.delete('root.txt')
        dirs, files = self.backend.listdir('')
        self.assertListEqual(dirs, ['images', 'css', 'js'])
        self.assertListEqual(files, [])

    @patch('tests.utils.FakeSwift.objects', new=deepcopy(CONTAINER_CONTENTS))
    def test_save(self):
        """Save an object"""
        backend = self.default_storage('v3', container_name="data")
        name = backend._save("test.txt", "test")
        dirs, files = self.backend.listdir('')
        self.assertEqual(files.count(name), 1)

    def test_open(self):
        """Attempt to open a object"""
        file = self.backend._open('root.txt')
        self.assertEqual(file.name, 'root.txt')
        data = file.read()
        self.assertEqual(len(data), 4096)

    def test_get_available_name_nonexist(self):
        """Available name for non-existent object"""
        object = 'images/doesnotexist.png'
        name = self.backend.get_available_name(object)
        self.assertEqual(name, object)

    def test_get_available_name_exist(self):
        """Available name for non-existent object"""
        object = 'images/test.png'
        name = self.backend.get_available_name(object)
        self.assertNotEqual(name, object)
