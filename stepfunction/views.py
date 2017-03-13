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
    "taskToken": {
      "type": "string",
      "title": "taskToken",
      "description": "Task token"
    }
  }
}


The UISchema for the records is:

{
  "ui:order": [
    "stateMachineArn",
    "activityArn",
    "taskToken"
  ]
}

"""

from kinto.core import Service, logger
from kinto.core.storage.exceptions import RecordNotFoundError

stepfunction = Service(
    name="stepfunction",
    path='/buckets/stepfunction/collections/manual_steps/records/{record_id}/stepfunction',
    description="Stepfunction manual step")

@stepfunction.post()
def post_manual_step(request):
    record_id = request.matchdict['record_id']
    try:
        record = request.registry.storage.get(
            object_id=record_id,
            collection_id="record",
            parent_id="/buckets/stepfunction/collections/manual_steps")
    except RecordNotFoundError as error:
        # logger.exception(error)
        return {"error": "Record not found"}

    query = request.body

    access_key, secret_key = request.registry.aws_credentials
    print("Sending a POST to the aws stepfunction:", query)
    return record
