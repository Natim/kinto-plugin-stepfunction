"""stepfunction - A Kinto plugin for AWS stepfunction manual steps"""
from pyramid.settings import aslist


__version__ = '0.1.0'
__author__ = 'Mathieu Agopian <mathieu@agopian.info>'
__all__ = []


def includeme(config):
    print("I am the stepfunction plugin!")

    # Grab AWS credentials from the config
    config.registry.aws_credentials = load_from_config(config)

    # Activate end-points.
    config.scan('stepfunction.views')

    # Add capability, so it's exposed on the root url.
    config.add_api_capability(
        "stepfunction",
        description="Post a Fail or Succeed to an AWS stepfunction",
        url="https://my-super-indexer-for-kinto.org")


def load_from_config(config):
    settings = config.get_settings()
    access_key = settings.get('stepfunction.aws_access_key', '')
    secret_key = settings.get('stepfunction.aws_secret_key', '')
    return (access_key, secret_key)
