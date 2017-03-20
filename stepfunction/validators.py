import colander
from kinto.core.errors import http_error, httpexceptions, ERRORS
from kinto.core.storage.exceptions import RecordNotFoundError

from .storage import get_record


def record_validator(schema):
    def validator(request, **kwargs):
        try:
            record = get_record(request)
        except RecordNotFoundError:
            details = {
                "id": request.matchdict['id'],
                "resource_name": "record"
            }
            response = http_error(httpexceptions.HTTPNotFound(),
                                  errno=ERRORS.INVALID_RESOURCE_ID,
                                  details=details)
            raise response

        try:
            deserialized = schema.deserialize(record)
        except colander.Invalid as e:
            translate = request.localizer.translate
            error_dict = e.asdict(translate=translate)
            for name, msg in error_dict.items():
                request.errors.add('body', name, msg)
        else:
            request.validated['record'] = deserialized

    return validator
