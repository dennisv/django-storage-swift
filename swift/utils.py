from django.conf import settings

def setting(name, default=None):
    return getattr(settings, name, default)
