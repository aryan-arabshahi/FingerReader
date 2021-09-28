from dataclasses import dataclass, is_dataclass, asdict
from json import JSONEncoder, loads, dumps


class EnhancedJSONEncoder(JSONEncoder):

    def default(self, o):
        if is_dataclass(o):
            return asdict(o)

        return super().default(o)


class DataClass:

    def to_json(self, include: list = None, exclude: list = None) -> dict:
        """Convert dataclass to json

        Keyword Arguments:
            include {list} -- (default: {None})
            exclude {list} -- (default: {None})
        
        Returns:
            dict
        """

        data = loads(dumps(self, cls=EnhancedJSONEncoder))

        _exclude = exclude or []

        if include:
            result_fields = {}
            for field_name in include:
                result_fields[field_name] = data.get(field_name)
            return result_fields

        for excluded_field in _exclude:
            data.pop(excluded_field, None)

        return data


@dataclass
class SensorParameters(DataClass):
    id: int
    registration_status: int
    capacity: int
    security_level: int
    address: int
    packet_length: int
    baud_rate: int
