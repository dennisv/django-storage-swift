from setuptools import setup

setup(name='django-storage-swift',
      version='1.2.1',
      description='OpenStack Swift storage backend for Django',
      url='http://github.com/blacktorn/django-storage-swift',
      author='Dennis Vermeulen',
      author_email='blacktorn@gmail.com',
      license='MIT',
      packages=['swift'],
      install_requires=[
          'python-swiftclient==1.4.0',
          'python-keystoneclient==0.2.3',
      ],
      zip_safe=False)
