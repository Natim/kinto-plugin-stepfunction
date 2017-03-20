def get_activity_arn(record, client):
    """Get the activityArn from the record, and check it's in the list of
    activities waiting for an answer."""
    # Get the list of activities for this stepfunction, and make sure the
    # activityArn from the record is present in the list of activities waiting
    # for an answer.
    activity_arn = record['activityArn']
    activity_list = client.list_activities()
    activity_ARNs = [activity['activityArn'] for activity in activity_list['activities']]
    if activity_arn not in activity_ARNs:
        raise ValueError(
            "The activityArn doesn't correspond to a pending activity: {}".format(activity_ARNs))
    return activity_arn


def get_task_token(activity_arn, client):
    """Get the task token for an activity given its arn."""
    task_token = client.get_activity_task(
        activityArn=activity_arn,
        workerName='kinto-plugin-stepfunction')
    return task_token['taskToken']
