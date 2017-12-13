import sys, os
import collections
import json, pyaml

class Json2yaml():
    def safeopen(name, mode='r', buffering=1):
        return open(name, mode, buffering)

    def convert(json_file, yaml_file):
        loaded_json = json.load(json_file, object_pairs_hook=collections.OrderedDict)
        pyaml.dump(loaded_json, yaml_file, safe=True)

if __name__ == '__main__':


    json_arg = 'this_data.json'
    yaml_arg = 'this_data.yml'

    with Json2yaml.safeopen(json_arg, 'r') as json_file:
        with Json2yaml.safeopen(yaml_arg, 'w+') as yaml_file:
            Json2yaml.convert(json_file, yaml_file)