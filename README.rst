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


AWS setup (lambda functions and step functions)
-----------------------------------------------

First thing is to have a lambda function that posts a new record to Kinto with
the `stateMachineArn` and the `activityArn`::

    'use strict';

    const https = require('https');

    /**
     * Pass the data to send as `event.data`, and the request options as
     * `event.options`. For more information see the HTTPS module documentation
     * at https://nodejs.org/api/https.html.
     *
     * Will succeed with the response body.
     */
    exports.handler = (event, context, callback) => {
        const req = https.request(event.options, (res) => {
            let body = '';
            console.log('Status:', res.statusCode);
            console.log('Headers:', JSON.stringify(res.headers));
            res.setEncoding('utf8');
            res.on('data', (chunk) => body += chunk);
            res.on('end', () => {
                console.log('Successfully processed HTTPS response');
                // If we know it's JSON, parse it
                if (res.headers['content-type'] === 'application/json') {
                    body = JSON.parse(body);
                }
                callback(null, body);
            });
        });
        req.on('error', callback);
        req.write(JSON.stringify(event.data));
        req.end();
    };


Test the lambda with the following event::

    {
      "data": {
        "data": {
          "subject": "Please review and sign-off (or not) on this addon",
          "stateMachineArn": "arn:aws:states:us-west-2:927034868273:stateMachine:AddonSigningManualStep",
          "activityArn": "arn:aws:states:us-west-2:927034868273:activity:ManualStepTest"
        },
        "permissions": {
          "write": [
            "portier:email@example.com"
          ]
        }
      },
      "options": {
        "hostname": "kinto.dev.mozaws.net",
        "port": 443,
        "path": "/v1/buckets/stepfunction/collections/manual_steps/records",
        "method": "POST",
        "headers": {
          "Authorization": "Basic dGVzdDp0ZXN0"
        }
      }
    }


Now create a step function using this lambda::

    {
        "Comment": "A test using a manual step",
        "StartAt": "PostToKinto",
        "States": {
            "PostToKinto": {
                "Type": "Task",
                "Resource": "arn:aws:lambda:us-west-2:927034868273:function:PostToKinto",
                "Next": "ManualStep"
            },
            "ManualStep": {
                "Type": "Task",
                "Resource": "arn:aws:states:us-west-2:927034868273:activity:ManualStepTest",
                "TimeoutSeconds": 3600,
                "End": true
            }
        }
    }

When running this stepfunction, you can provide the previously tested event to
have the lambda create a new record on Kinto. Using this plugin, you can then
POST a `FAIL` or `SUCCEED` to
https://kinto.dev.mozaws.net/v1/buckets/stepfunction/collection/manual_steps/records/<record_id>/stepfunction
and it'll update the stepfunction execution accordingly.


Authors
-------

`stepfunction` was written by `Mathieu Agopian <mathieu@agopian.info>`_.
