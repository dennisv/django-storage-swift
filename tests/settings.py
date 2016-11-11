import os

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
SECRET_KEY = '95mk9r=y^bvver#6e#-169t9brqpcq#&@gjk*#!3lckf&#9)p3'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_DIR, 'test.db')
    }
}

# SWIFT_AUTH_URL = 'https://objects.example.com'
# SWIFT_USERNAME = 'user'
# SWIFT_PASSWORD = 'password'
# SWIFT_TENANT_ID = '11223344556677889900aabbccddeeff'
# SWIFT_CONTAINER_NAME = 'www-media'
# SWIFT_STATIC_CONTAINER_NAME = 'www-static'
