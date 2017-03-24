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

Lambda function: build data for kinto
_____________________________________

First thing is to have a lambda function that massages the input data (a
subject, a list of email addresses for the reviewers, the ARN for the
stepfunction and the ARN for the manual step task) into data that will be
posted to Kinto::

    'use strict';

    // expects the event to have the following shape:
    // { "subject": "Please review and sign-off (or not) on this addon",
    //   "reviewers": ["<email1@example.com>", "<email2@example.com>", ...],
    //   "stateMachineArn": "<the stepfunction ARN here>",
    //   "activityArn": "<the manual step ARN here>"}
    exports.handler = (event, context) => {
      const requests = event.reviewers.map(function (reviewer) {
        return {
          "body": {
            "data": {
              "subject": event.subject,
              "stateMachineArn": event.stateMachineArn,
              "activityArn": event.activityArn,
              "reviewer": reviewer
            },
            "permissions": {
              "write": [
                "portier:" + reviewer
              ]
            }
          }
        }
      });

      context.succeed({
        "data": {
          "defaults": {
            "method": "POST",
            "path": "/v1/buckets/stepfunction/collections/manual_steps/records"
          },
          "requests": requests
        },
        "options": {
          "hostname": "kinto.dev.mozaws.net",
          "port": 443,
          "path": "/v1/buckets/stepfunction/collections/manual_steps/records",
          "path": "/v1/batch",
          "method": "POST",
          "headers": {
            "Authorization": "Basic dGVzdDp0ZXN0"
          }
        }
      })
    };

This lambda function can then be tested with the following input::

    { "subject": "Please review and sign-off (or not) on this addon",
      "reviewers": ["<email1@example.com>", "<email2@example.com>"],
      "stateMachineArn": "<the stepfunction ARN here>",
      "activityArn": "<the manual step ARN here>"}


Lambda function: Post new records to Kinto
__________________________________________

First thing is to have a lambda function that posts new records to Kinto for
each manual step (for each reviewer) with the `stateMachineArn` and the
`activityArn`. The following lambda is a very generic node function that posts
a request::

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


Test the lambda with the following event (the bucket and collection need to
exist already, check the `stepfunction/views.py` docstring for the schemas to
use)::

    {
      "data": {
        "data": {
          "subject": "Please review and sign-off (or not) on this addon",
          "stateMachineArn": "arn:aws:states:us-west-2:927034868273:stateMachine:AddonSigningManualStep",
          "activityArn": "arn:aws:states:us-west-2:927034868273:activity:ManualStepTest",
          "reviewer": "<reviewer email address here>"
        },
        "permissions": {
          "write": [
            "portier:<reviewer email address here>"
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


Lambda function: send an email to the reviewer
______________________________________________

Once the record is created in Kinto, we need to warn the reviewer that it's
waiting for them. Create a new lambda function::

    'use strict';
    console.log('Loading function');
    const aws = require('aws-sdk');
    const ses = new aws.SES();

    exports.handler = (event, context, callback) => {
      const recipients = event;
      console.log('Send an email to', recipients);

      var emailParams = {
        Destination: {
          ToAddresses: recipients
        },
        Message: {
          Subject: {
            Data: 'Your review needed for an add-on!',
            Charset: 'UTF-8'
          },
          Body: {
            Html: {
              Data: 'Hi!<br />' +
                    'Can you please review the add-on, and then head to<br />' +
                    'https://addons-shipping.github.io/stepfunction-dashboard/' +
                    '<br />to accept or reject? Thanks!',
              Charset: 'UTF-8'
            }
          }
        },
        Source: 'storage-team@dev.mozaws.net',
        ReplyToAddresses: [
          'storage-team@dev.mozaws.net'
        ]
      };

      ses.sendEmail(emailParams, function (err, data) {
        if (err) {
          console.log(err, err.stack);
          context.fail('Internal Error: The email could not be sent.');
        } else {
          console.log(data);
          context.succeed('The email was successfully sent.');
        }
      });
    };

Test the lambda with the following event::

    [<first email here>, <second email here>]


One stepfunction to bring them all and in aws bind them
_______________________________________________________

To glue all of those together, we'll create a stepfunction. Before that, we
just need to helper lambdas: one to count the number of reviews needed, and one
to decrement the number of reviews still needed::

    exports.handler = (event, context) => {
        context.succeed(event.length)
    };

and

::

    exports.handler = (event, context, callback) => {
        context.succeed(event - 1);
    };


Now create a step function using those lambda functions::

    {
        "Comment": "Ask for add-on reviews before signing them",
        "StartAt": "BuildDataForKinto",
        "States": {
            "BuildDataForKinto": {
                "Type": "Task",
                "Resource": "arn:aws:lambda:us-west-2:927034868273:function:BuildDataForKinto",
                "Next": "PostToKinto",
                "ResultPath": "$.requests"
            },
            "PostToKinto": {
                "Type": "Task",
                "InputPath": "$.requests",
                "Resource": "arn:aws:lambda:us-west-2:927034868273:function:PostToKinto",
                "Next": "NotifyReviewers",
                "ResultPath": "$.postedToKinto"
            },
            "NotifyReviewers": {
                "Type": "Task",
                "InputPath": "$.reviewers",
                "Resource": "arn:aws:lambda:us-west-2:927034868273:function:AddonSigningNotifyReviewer",
                "Next": "CountReviewsNeeded",
                "ResultPath": "$.notified"
            },
            "CountReviewsNeeded": {
                "Type": "Task",
                "Resource": "arn:aws:lambda:us-west-2:927034868273:function:ListLength",
                "InputPath": "$.reviewers",
                "ResultPath": "$.reviews",
                "Next": "WaitForReviews"
            },
            "WaitForReviews": {
                "Type": "Choice",
                "Choices": [
                    {
                        "Variable": "$.reviews",
                        "NumericGreaterThan": 0,
                        "Next": "WaitForReview"
                    }
                ],
                "Default": "SignAddon"
            },
            "WaitForReview": {
                "Type": "Task",
                "Resource": "arn:aws:states:us-west-2:927034868273:activity:ManualStepTest",
                "TimeoutSeconds": 3600,
                "ResultPath": "$.reviewed",
                "Next": "UpdateReviews"
            },
            "UpdateReviews": {
                "Type": "Task",
                "Resource": "arn:aws:lambda:us-west-2:927034868273:function:SubtractOne",
                "InputPath": "$.reviews",
                "ResultPath": "$.reviews",
                "Next": "WaitForReviews"
            },
            "SignAddon": {
                "Type": "Task",
                "Resource": "arn:aws:lambda:us-west-2:927034868273:function:addons_sign-xpi",
                "ResultPath": "$.signed",
                "End": true
            }
        }
    }

When running this stepfunction, you can use the following event to have the
lambda create a record for each reviewer on Kinto::

    {
      "subject": "Please review and sign-off (or not) on this addon",
      "reviewers": ["<email1@example.com>", "<email2@example.com>"],
      "stateMachineArn": "arn:aws:states:us-west-2:927034868273:stateMachine:AddonSigning",
      "activityArn": "arn:aws:states:us-west-2:927034868273:activity:ManualStepTest",
      "url": "<url of the add-on XPI to sign>",
      "checksum": "<sha256 of the add-on>"
    }


Using this plugin, you can then POST a `FAIL` or `SUCCEED` to
https://kinto.dev.mozaws.net/v1/buckets/stepfunction/collection/manual_steps/records/<record_id>/stepfunction
and it'll update the stepfunction execution accordingly.

The most convenient way to do this POST is via
https://addons-shipping.github.io/stepfunction-dashboard/


Authors
-------

`stepfunction` was written by `Mathieu Agopian <mathieu@agopian.info>`_.
