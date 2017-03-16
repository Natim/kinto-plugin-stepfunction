stepfunction: a kinto plugin
============================

A Kinto plugin for AWS stepfunction manual steps

Usage
-----

You'll need to add `stepfunction` to the `kinto.includes` section in your
`config.ini` file::

    kinto.includes =
        stepfunction

And then configure your AWS credentials::

    stepfunction.aws_access_key = <your AWS access key here>
    stepfunction.aws_secret_key = <your AWS secret key here>

Check the `stepfunction/views.py` docstring to see the schema for the record
that this plugin is expecting to have.


Authors
-------

`stepfunction` was written by `Mathieu Agopian <mathieu@agopian.info>`_.
