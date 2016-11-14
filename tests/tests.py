from copy import deepcopy
from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
from mock import patch
from .utils import FakeSwift, auth_params, base_url, CONTAINER_CONTENTS, TENANT_ID
from swift import storage


class SwiftStorageTestCase(TestCase):

    def default_storage(self, auth_version, exclude=None, **params):
        """Instantiate default storage with auth parameters"""
        return storage.SwiftStorage(**auth_params(auth_version, exclude=exclude, **params))

    def static_storage(self, auth_version, exclude=None, **params):
        """Instantiate static storage with auth parameters"""
        return storage.StaticSwiftStorage(**auth_params(auth_version, exclude=exclude, **params))


@patch('swift.storage.swiftclient', new=FakeSwift)
class AuthTest(SwiftStorageTestCase):
    """Test authentication parameters"""

    def test_auth_v1(self):
        """Test version 1 authentication"""
        self.default_storage('v1')

    def test_auth_v2(self):
        """Test version 2 authentication"""
        self.default_storage('v2')

    def test_auth_v3(self):
        """Test version 3 authentication"""
        self.default_storage('v3')

    def test_auth_v1_detect_version(self):
        """Test version 1 authentication detection"""
        backend = self.default_storage('v1', exclude=['auth_version'])
        self.assertEqual(backend.auth_version, '1')

    def test_auth_v2_detect_version(self):
        """Test version 2 authentication detection"""
        backend = self.default_storage('v2', exclude=['auth_version'])
        self.assertEqual(backend.auth_version, '2')

    def test_auth_v3_detect_version(self):
        """Test version 3 authentication detection"""
        backend = self.default_storage('v3', exclude=['auth_version'])
        self.assertEqual(backend.auth_version, '3')

    def test_auth_v2_no_tenant(self):
        """Missing tenant in v2 auth"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v2', exclude=['tenant_name', 'tenant_id'])

    def test_auth_v3_no_user_domain(self):
        """Missing user_domain in v3 auth"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', exclude=['user_domain_name', 'user_domain_id'])

    def test_auth_v3_no_project_domain(self):
        """Missing project_domain in v3 auth"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', exclude=['project_domain_name', 'project_domain_id'])


@patch('swift.storage.swiftclient', new=FakeSwift)
class MandatoryParamsTest(SwiftStorageTestCase):

    def test_instantiate_default(self):
        """Instantiate default backend with no parameters"""
        with self.assertRaises(ImproperlyConfigured):
            storage.SwiftStorage()

    def test_instantiate_static(self):
        """Instantiate static backend with no parameters"""
        with self.assertRaises(ImproperlyConfigured):
            storage.StaticSwiftStorage()

    def test_mandatory_auth_url(self):
        """Test ImproperlyConfigured if api_auth_url is missing"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', exclude=['api_auth_url'])

    def test_mandatory_username(self):
        """Test ImproperlyConfigured if api_auth_url is missing"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', exclude=['api_username'])

    def test_mandatory_container_name(self):
        """Test ImproperlyConfigured if container_name is missing"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', exclude=['container_name'])

    def test_mandatory_static_container_name(self):
        """Test ImproperlyConfigured if container_name is missing"""
        with self.assertRaises(ImproperlyConfigured):
            self.static_storage('v3', exclude=['container_name'])

    def test_mandatory_password(self):
        """Test ImproperlyConfigured if api_key is missing"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', exclude=['api_key'])


@patch('swift.storage.swiftclient', new=FakeSwift)
class ConfigTest(SwiftStorageTestCase):

    def test_auto_base_url(self):
        """Automatically resolve base url"""
        backend = self.default_storage('v3', auto_base_url=True)
        self.assertEqual(backend.base_url, base_url(container="container"))

    def test_override_base_url_no_auto(self):
        """Test overriding base url without auto base url"""
        url = 'http://localhost:8080/test/'
        backend = self.default_storage('v3',
                                       auto_base_url=False,
                                       override_base_url=url)
        self.assertEqual(backend.base_url, url)

    def test_override_base_url_auto(self):
        """Test overriding base url with auto"""
        url = 'http://localhost:8080'
        backend = self.default_storage('v3',
                                       auto_base_url=True,
                                       override_base_url=url)
        self.assertTrue(backend.base_url.startswith(url))
        storage_url = '{}/v1/AUTH_{}/{}/'.format(url, TENANT_ID, "container")
        self.assertEqual(backend.base_url, storage_url)


@patch('swift.storage.swiftclient', new=FakeSwift)
class TokenTest(SwiftStorageTestCase):

    def test_get_token(self):
        """Renewing token"""
        backend = self.default_storage('v3', auth_token_duration=0)
        backend.get_token()

    def test_set_token(self):
        """Set token manually"""
        backend = self.default_storage('v3', auth_token_duration=0)
        backend.set_token('token')


@patch('swift.storage.swiftclient', new=FakeSwift)
class CreateContainerTest(SwiftStorageTestCase):

    def test_auto_create_container(self):
        """Auth create container"""
        self.default_storage(
            'v3',
            auto_create_container=True,
            auto_create_container_public=True,
            auto_create_container_allow_orgin=True,
            container_name='new')


@patch('swift.storage.swiftclient', new=FakeSwift)
class BackendTest(SwiftStorageTestCase):

    @patch('swift.storage.swiftclient', new=FakeSwift)
    def setUp(self):
        self.backend = self.default_storage('v3')

    def test_url(self):
        """Get url for a resource"""
        name = 'images/test.png'
        url = self.backend.url(name)
        self.assertEqual(url, base_url(container=self.backend.container_name, path=name))

    def test_object_size(self):
        """Test getting object size"""
        size = self.backend.size('images/test.png')
        self.assertEqual(size, 4096)

    def test_modified_time(self):
        """Test getting modified time of an object"""
        self.backend.modified_time('images/test.png')

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
        backend = self.default_storage('v3')
        backend.rmtree('images')
        dirs, files = self.backend.listdir('')
        self.assertListEqual(dirs, ['css', 'js'])
        self.assertListEqual(files, ['root.txt'])

    @patch('tests.utils.FakeSwift.objects', new=deepcopy(CONTAINER_CONTENTS))
    def test_mkdirs(self):
        """Make directory/pseudofolder in backend"""
        backend = self.default_storage('v3')
        backend.makedirs('downloads')
        dirs, files = self.backend.listdir('')
        self.assertListEqual(dirs, ['images', 'css', 'js', 'downloads'])
        self.assertListEqual(files, ['root.txt'])

    @patch('tests.utils.FakeSwift.objects', new=deepcopy(CONTAINER_CONTENTS))
    def test_delete_object(self):
        """Delete an object"""
        backend = self.default_storage('v3')
        backend.delete('root.txt')
        dirs, files = self.backend.listdir('')
        self.assertListEqual(dirs, ['images', 'css', 'js'])
        self.assertListEqual(files, [])

    @patch('tests.utils.FakeSwift.objects', new=deepcopy(CONTAINER_CONTENTS))
    def test_save(self):
        """Save an object"""
        backend = self.default_storage('v3')
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
        """Available name for existing object"""
        object = 'images/test.png'
        name = self.backend.get_available_name(object)
        self.assertNotEqual(name, object)
