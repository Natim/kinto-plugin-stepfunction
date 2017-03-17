"""The schema for the records is:

{
  "type": "object",
  "properties": {
    "stateMachineArn": {
      "type": "string",
      "title": "stateMachineArn",
      "description": "ARN for the step machine (stepfunction)"
    },
    "activityArn": {
      "type": "string",
      "title": "activityArn",
      "description": "ARN for the activity (task aka manual step)"
    },
    "status": {
      "type": "string",
      "title": "status",
      "description": "Status of the step, FAIL or SUCCEED",
      "enum": [
        "Unanswered",
        "Fail",
        "Succeed"
      ],
      "default": "Unanswered"
    }
  }
}


The UISchema for the records is:

{
  "ui:order": [
    "stateMachineArn",
    "activityArn",
    "status"
  ]
}

The POST body expects to have an "answer" key which is either "FAIL" or
"SUCCEED". This message will then be sent to the stepfunction activity.

"""

import boto3
import colander

from cornice.validators import colander_body_validator
from kinto.core import Service
from kinto.core.errors import http_error, ERRORS
from pyramid import httpexceptions


from .s3 import get_activity_arn, get_task_token
from .storage import update_record
from .validators import record_validator


stepfunction = Service(
    name="stepfunction",
    path='/buckets/{bucket_id}/collections/{collection_id}/records/{record_id}/stepfunction',
    description="Stepfunction manual step")


class RecordSchema(colander.MappingSchema):
    id = colander.SchemaNode(colander.String())
    activityArn = colander.SchemaNode(colander.String())
    taskToken = colander.SchemaNode(colander.String(), missing=colander.drop)


class AnswerRequestSchema(colander.MappingSchema):
    answer = colander.SchemaNode(colander.String(),
                                 validator=colander.OneOf(["FAIL", "SUCCEED"]),
                                 required=True)


@stepfunction.post(schema=AnswerRequestSchema(),
                   validators=(colander_body_validator, record_validator(RecordSchema())))
def post_manual_step(request):
    # Get the record.
    answer = request.validated['answer']
    record = request.validated['record']
    try:
        # Set up an AWS stepfunction client.
        access_key, secret_key = request.registry.aws_credentials
        client = boto3.client(
            'stepfunctions',
            region_name='us-west-2',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key)

        # Make sure the activity we have in the record is still pending.
        activity_arn = get_activity_arn(record, client)
        print("activityArn:", activity_arn)

        # And get its task token if we didn't already have it.
        task_token = record.get('taskToken')
        if task_token is None:
            task_token = get_task_token(activity_arn, client)
            print("Got task token:", task_token)
            record['taskToken'] = task_token
            update_record(request.registry.storage, record)

        # Post a succeed or fail to the stepfunction's activity.
        if answer == "FAIL":
            print("Sending a FAIL to the aws stepfunction")
            client.send_task_failure(
                taskToken=task_token,
                error="Not signing off",
                cause="After reviewing, the decision was made to not sign off")
            record['status'] = "FAIL"
        else:
            print("Sending a SUCCEED to the aws stepfunction")
            client.send_task_success(
                taskToken=task_token,
                output='{"message": "signed off"}')
            record['status'] = "SUCCEED"
        update_record(request.registry.storage, record)
    except Exception as err:
        raise http_error(httpexceptions.HTTPServiceUnavailable,
                         errno=ERRORS.BACKEND,
                         message=err)
