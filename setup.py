from setuptools import setup

setup(name='django-storage-swift',
      version='1.1',
      description='OpenStack Swift storage backend for Django',
      url='http://github.com/wecreatepixels/django-storage-swift',
      author='Dennis Vermeulen',
      author_email='dennis@wecreatepixels.nl',
      license='MIT',
      packages=['swift'],
      install_requires=[
          'python-swiftclient==1.4.0',
          'python-keystoneclient==0.2.3',
      ],
      zip_safe=False)
