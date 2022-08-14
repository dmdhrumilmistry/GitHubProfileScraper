import json
from threading import Thread


class ThreadHandler(Thread):
    '''class to handle threads with result'''
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None):
        def function():
            self.result = target(*args, **kwargs)
        super().__init__(group=group, target=function, name=name, daemon=daemon)


def sanitize_html_text(text: str) -> str:
    '''sanitizes html text to be used as str'''
    assert isinstance(text, str)

    return text.replace('\n', '').strip()


def write_json(file_name: str, data: dict):
    '''writes dict object into a json file, overwrites data if file already exists'''
    assert isinstance(file_name, str)
    assert isinstance(data, dict)

    with open(file_name, 'w') as f:
        f.write(json.dumps(data))
