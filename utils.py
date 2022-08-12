import json


def write_json(file_name:str, data:dict):
    '''writes dict object into a json file, overwrites data if file already exists'''
    assert isinstance(file_name, str)
    assert isinstance(data, dict)

    with open(file_name, 'w') as f:
        f.write(json.dumps(data, indent=4))