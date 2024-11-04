import json


def log(tag, *messages):
    for message in messages:
        if isinstance(message, (dict, list)):
            message = json.dumps(message, indent=2)
        
        print("{begin_color}{tag}: {message}{end_color}".format(
            tag=tag,
            message=message,
            begin_color=get_tag_color(tag),
            end_color="\x1B[0m",
        ))


def get_tag_color(tag):
    if tag == "debug":
        return "\033[93m"
    elif tag == "info":
        return "\033[96m"
    elif tag == "warning":
        return "\033[93m"
    elif tag == "error":
        return "\033[93m"
    return ""
