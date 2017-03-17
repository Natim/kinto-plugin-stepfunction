from kinto.core.utils import instance_uri


def get_record(request):
    return request.registry.storage.get(
        object_id=request.matchdict['record_id'],
        collection_id="record",
        parent_id=instance_uri(request, 'collection',
                               bucket_id=request.matchdict['bucket_id'],
                               id=request.matchdict['collection_id']))


def update_record(storage, record):
    """Save the record in the database."""
    storage.update(
        object_id=record['id'],
        collection_id="record",
        parent_id="/buckets/stepfunction/collections/manual_steps",
        record=record)
