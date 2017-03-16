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
from kinto.core import Service, logger
from kinto.core.storage.exceptions import RecordNotFoundError

stepfunction = Service(
    name="stepfunction",
    path='/buckets/stepfunction/collections/manual_steps/records/{record_id}/stepfunction',
    description="Stepfunction manual step")


def get_answer_from_body(request):
    """Return the answer if the body was properly parsed, or raise."""
    try:
        query = request.json
    except ValueError as err:
        raise Exception("The body couldn't be parsed to json: ".format(err))

    answer = query.get('answer', None)
    if answer is None:
        raise Exception("The body needs an 'answer' (FAIL or SUCCEED)")
    if answer not in ['FAIL', 'SUCCEED']:
        raise Exception("The answer must be FAIL or SUCCEED")
    return answer


def get_activity_arn(record, client):
    """Get the activityArn from the record, and check it's in the list of
    activities waiting for an answer."""
    # Get the list of activities for this stepfunction, and make sure the
    # activityArn from the record is present in the list of activities waiting
    # for an answer.
    activity_arn = record.get('activityArn', None)
    if activity_arn is None:
        raise Exception("The record doesn't have an activityArn")
    activity_list = client.list_activities()
    activity_ARNs = [
        activity['activityArn']
        for activity in activity_list['activities']]
    if activity_arn not in activity_ARNs:
        raise Exception(
            "The activiryArn doesn't correspond to a pending activity")
    return activity_arn


def get_task_token(activity_arn, client):
    """Get the task token for an activity given its arn."""
    task_token = client.get_activity_task(
        activityArn=activity_arn,
        workerName='kinto-plugin-stepfunction')
    return task_token['taskToken']


@stepfunction.post()
def post_manual_step(request):
    # Get the record.
    record_id = request.matchdict['record_id']
    try:
        record = request.registry.storage.get(
            object_id=record_id,
            collection_id="record",
            parent_id="/buckets/stepfunction/collections/manual_steps")
    except RecordNotFoundError as error:
        # logger.exception(error)
        return {"error": "Record not found"}

    try:
        # Get the answer from the POST request's body.
        answer = get_answer_from_body(request)
        print("answer:", answer)

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

        # And get its task token.
        task_token = get_task_token(activity_arn, client)
        print("Task token:", task_token)


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
        request.registry.storage.update(
            object_id=record_id,
            collection_id="record",
            parent_id="/buckets/stepfunction/collections/manual_steps",
            record=record)
    except Exception as err:
        return {"error": err}
