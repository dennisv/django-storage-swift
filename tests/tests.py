# -*- coding: UTF-8 -*-
import hmac
from copy import deepcopy
from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured, SuspiciousFileOperation
from django.core.files.base import ContentFile
from hashlib import sha1
from mock import patch
from .utils import FakeSwift, auth_params, base_url, CONTAINER_CONTENTS, TENANT_ID
from swift import storage
from six.moves.urllib import parse as urlparse


class SwiftStorageTestCase(TestCase):

    def default_storage(self, auth_config, exclude=None, **params):
        """Instantiate default storage with auth parameters"""
        return storage.SwiftStorage(**auth_params(auth_config, exclude=exclude, **params))

    def static_storage(self, auth_config, exclude=None, **params):
        """Instantiate static storage with auth parameters"""
        return storage.StaticSwiftStorage(**auth_params(auth_config, exclude=exclude, **params))


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

    def test_auth_v3_no_tenant(self):
        """Missing tenant in v3 auth"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', exclude=['tenant_name'])

    def test_auth_v3_no_user_domain(self):
        """Missing user_domain in v3 auth"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', exclude=['user_domain_name', 'user_domain_id'])

    def test_auth_v3_no_project_domain(self):
        """Missing project_domain in v3 auth"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', exclude=['project_domain_name', 'project_domain_id'])

    def test_auth_v3_int_auth_version(self):
        """Auth version converts into a string"""
        backend = self.default_storage('v3', auth_version=3)
        self.assertEqual(backend.auth_version, '3')


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

    def test_missing_container(self):
        """Raise if container don't exist"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', container_name='idontexist')

    def test_delete_nonexisting_file(self):
        """Deleting non-existing file is silently ignored"""
        backend = self.default_storage('v3')
        backend.delete("idontexist.something")

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

    def test_illegal_extra_opts(self):
        """extra_opts should always be a dict"""
        with self.assertRaises(ImproperlyConfigured):
            self.default_storage('v3', os_extra_options="boom!")

    @patch.object(FakeSwift.Connection, '__init__', return_value=None)
    def test_override_lazy_connect(self, mock_swift_init):
        """Test setting lazy_connect delays connection creation"""
        backend = self.default_storage('v3', lazy_connect=True)
        assert not mock_swift_init.called
        self.assertFalse(backend.exists('warez/some_random_movie.mp4'))
        assert mock_swift_init.called


# @patch('swift.storage.swiftclient', new=FakeSwift)
# class TokenTest(SwiftStorageTestCase):

#     def test_get_token(self):
#         """Renewing token"""
#         backend = self.default_storage('v3', auth_token_duration=0)
#         backend.get_token()

#     def test_set_token(self):
#         """Set token manually"""
#         backend = self.default_storage('v3', auth_token_duration=0)
#         backend.set_token('token')


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

    def test_url_unicode_name(self):
        """Get url for a resource with unicode filename"""
        name = u'images/test终端.png'
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
        content_file = ContentFile("Hello world!")
        name = backend.save("test.txt", content_file)
        dirs, files = self.backend.listdir('')
        self.assertEqual(files.count(name), 1)

    @patch('tests.utils.FakeSwift.objects', new=deepcopy(CONTAINER_CONTENTS))
    @patch('gzip.GzipFile')
    def test_save_gzip(self, gzip_mock):
        """Save an object"""
        backend = self.default_storage('v3')
        backend.gzip_content_types = ['text/plain']
        content_file = ContentFile(b'Hello world!')
        name = backend.save('testgz.txt', content_file)
        dirs, files = self.backend.listdir('')
        self.assertEqual(files.count(name), 1)
        self.assertTrue(gzip_mock.called)

    @patch('tests.utils.FakeSwift.objects', new=deepcopy(CONTAINER_CONTENTS))
    def test_content_type_from_fd(self):
        """Test content_type detection on save"""
        backend = self.default_storage('v3', content_type_from_fd=True)
        backend.save("test.txt", ContentFile("Some random data"))

    def test_save_non_rewound(self):
        """Save file with position not at the beginning"""
        content = dict(orig=b"Hello world!")
        content_file = ContentFile(content['orig'])
        content_file.seek(5)

        def mocked_put_object(cls, url, token, container, name=None,
                              contents=None, content_length=None, *args, **kwargs):
            content['saved'] = contents.read()
            content['size'] = content_length

        with patch('tests.utils.FakeSwift.put_object', new=classmethod(mocked_put_object)):
            self.backend.save('test.txt', content_file)
        self.assertEqual(content['saved'], content['orig'])
        self.assertEqual(content['size'], len(content['orig']))

    def test_no_content_length_from_fd(self):
        """Test disabling content_length_from_fd on save"""
        backend = self.default_storage('v3', content_length_from_fd=False)
        content = dict(orig="Hello world!")
        content_file = ContentFile("")
        content_file.write(content['orig'])

        def mocked_put_object(cls, url, token, container, name=None,
                              contents=None, content_length=None, *args, **kwargs):
            content['saved'] = contents.read()
            content['size'] = content_length

        with patch('tests.utils.FakeSwift.put_object', new=classmethod(mocked_put_object)):
            backend.save('test.txt', content_file)
        self.assertEqual(content['saved'], content['orig'])
        self.assertIsNone(content['size'])

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

    def test_get_available_name_max_length_nonexist(self):
        """Available name with max_length for non-existent object"""
        object = 'images/doesnotexist.png'
        name = self.backend.get_available_name(object, len(object))
        self.assertEqual(name, object)
        with self.assertRaises(SuspiciousFileOperation):
            name = self.backend.get_available_name(object, 16)

    def test_get_available_name_exist(self):
        """Available name for existing object"""
        object = 'images/test.png'
        name = self.backend.get_available_name(object)
        self.assertNotEqual(name, object)

    def test_get_available_name_max_length_exist(self):
        """Available name with max_length for existing object"""
        object = 'images/test.png'
        name = self.backend.get_available_name(object, 32)
        self.assertNotEqual(name, object)

    def test_get_available_name_prefix(self):
        """Available name with prefix"""
        object = 'test.png'
        # This will add the prefix, then get_avail will remove it again
        backend = self.default_storage('v3', name_prefix="prefix-")
        name = backend.get_available_name(object)
        self.assertEqual(object, name)

    def test_get_available_name_static(self):
        """Static's get_available_name should be unmodified"""
        static = self.static_storage('v3')
        object = "test.txt"
        name = static.get_available_name(object)
        self.assertEqual(name, object)

    def test_get_valid_name(self):
        name = self.backend.get_valid_name("A @#!file.txt")
        self.assertEqual(name, "A_file.txt")

    def test_path(self):
        """path is not implemented"""
        with self.assertRaises(NotImplementedError):
            self.backend.path("test.txt")


@patch('swift.storage.swiftclient', new=FakeSwift)
class TemporaryUrlTest(SwiftStorageTestCase):

    def assert_valid_temp_url(self, name):
        url = self.backend.url(name)
        split_url = urlparse.urlsplit(url)
        query_params = urlparse.parse_qs(split_url[3])
        split_base_url = urlparse.urlsplit(base_url(container=self.backend.container_name, path=name))

        # ensure scheme, netloc, and path are same as to non-temporary URL
        self.assertEqual(split_base_url[0:2], split_url[0:2])

        # ensure query string contains signature and expiry
        self.assertIn('temp_url_sig', query_params)
        self.assertIn('temp_url_expires', query_params)

    def assert_valid_signature(self, path):
        """Validate temp-url signature"""
        backend = self.default_storage('v3', use_temp_urls=True, temp_url_key='Key')
        url = backend.url(path)
        url_parsed = urlparse.urlsplit(url)
        params = urlparse.parse_qs(url_parsed.query)
        msg = "{}\n{}\n{}".format("GET", params['temp_url_expires'][0], urlparse.unquote(url_parsed.path))
        sig = hmac.new(backend.temp_url_key, msg.encode('utf-8'), sha1).hexdigest()
        self.assertEqual(params['temp_url_sig'][0], sig)

    def test_signature(self):
        self.assert_valid_signature("test/test.txt")
        self.assert_valid_signature("test/file with spaces.txt")

    def test_temp_url_key_required(self):
        """Must set temp_url_key when use_temp_urls=True"""
        with self.assertRaises(ImproperlyConfigured):
            self.backend = self.default_storage('v3', use_temp_urls=True)

    def test_temp_url_key(self):
        """Get temporary url using string key"""
        self.backend = self.default_storage('v3', use_temp_urls=True, temp_url_key='Key')
        self.assert_valid_temp_url('images/test.png')

    def test_temp_url_key_unicode(self):
        """temp_url_key must be ascii"""
        with self.assertRaises(ImproperlyConfigured):
            self.backend = self.default_storage('v3', use_temp_urls=True, temp_url_key=u'aあä')

    def test_temp_url_key_unicode_latin(self):
        """Get temporary url using a unicode key which can be ascii-encoded"""
        self.backend = self.default_storage('v3', use_temp_urls=True, temp_url_key=u'Key')
        self.assert_valid_temp_url('images/test.png')

    def test_temp_url_unicode_name(self):
        """temp_url file name can be unicode."""
        self.backend = self.default_storage('v3', use_temp_urls=True, temp_url_key=u'Key')
        self.assert_valid_temp_url('images/aあä.png')
