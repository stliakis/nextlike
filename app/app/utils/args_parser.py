from optparse import OptionParser

from app.utils.base import listify


class Argument(object):
    def __init__(self, name, dest, help=None, required=False):
        self.names = listify(name)
        self.dest = dest
        self.help = help
        self.required = required


class FlagArgument(object):
    def __init__(self, name, dest, help=None, required=False):
        self.names = listify(name)
        self.dest = dest
        self.help = help
        self.required = required


def get_args(*arguments):
    parser = OptionParser()
    for argument in arguments:
        if isinstance(argument, Argument):
            parser.add_option(*argument.names, dest=argument.dest,
                              help=argument.help)
        elif isinstance(argument, FlagArgument):
            parser.add_option(*argument.names, dest=argument.dest, action="store_true",
                              help=argument.help)

    (options, args) = parser.parse_args()

    for argument in arguments:
        if argument.required and not getattr(options, argument.dest):
            raise Exception("Missing required argument %s" % argument.names)

    return options
