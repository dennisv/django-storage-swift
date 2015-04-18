from setuptools import setup

setup(
    name='django-storage-swift',
    version='1.2.4',
    description='OpenStack Swift storage backend for Django',
    url='http://github.com/blacktorn/django-storage-swift',
    author='Dennis Vermeulen',
    author_email='blacktorn@gmail.com',
    license='MIT',
    packages=['swift'],
    install_requires=[
        'python-swiftclient>=1.4.0',
        'python-keystoneclient>=0.2.3',
        'six',
    ],
    zip_safe=False,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
)
