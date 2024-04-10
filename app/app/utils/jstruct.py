import json


class JStruct(dict):
    """
    The faster little brother of an old JStruct implementation
    use it just as a jstruct...  a=JStruct({"a":{"b":1}})
    """

    def __getattr__(self, item):
        if item not in self:
            return JStruct({})

        value = self.get(item)
        if isinstance(value, dict):
            return JStruct(value)
        elif isinstance(value, list):
            return [JStruct(i) if isinstance(i, (dict, list)) else i for i in value]
        else:
            return value

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __str__(self):
        return "JStruct(%s)" % json.dumps(self, indent=4)
