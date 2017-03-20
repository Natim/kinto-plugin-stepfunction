import setuptools

setuptools.setup(
    name="stepfunction",
    version="0.1.0",
    url="https://github.com/magopian/kinto-plugin-stepfunction",

    author="Mathieu Agopian",
    author_email="mathieu@agopian.info",

    description="A Kinto plugin for AWS stepfunction manual steps",
    long_description=open('README.rst').read(),

    packages=setuptools.find_packages(),

    install_requires=[
        'boto3',
        'colander',
        'kinto',
    ],

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
