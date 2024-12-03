import json


class JStruct(dict):
    """JStruct class for handle json objects as attributes."""

    def __getattr__(self, item):
        if item not in self:
            return JStruct({})

        return self._to_jstruct_or_value(self.get(item))

    def _to_jstruct_or_value(self, value):
        if isinstance(value, dict):
            return JStruct(value)
        elif isinstance(value, list):
            return [JStruct(i) if isinstance(i, dict) else i for i in value]
        else:
            return value

    @property
    def items(self):
        return self._to_jstruct_or_value(self.get("items"))

    @property
    def values(self):
        return self._to_jstruct_or_value(self.get("values"))

    @property
    def keys(self):
        return self._to_jstruct_or_value(self.get("keys"))

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __str__(self):
        return "JStruct(%s)" % json.dumps(dict(self), indent=4)

    def __repr__(self):
        return self.__str__()
