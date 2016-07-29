# -*-  coding: utf-8 -*-

import json
import sys

with open(sys.argv[1], "r") as f:
    data = json.load(f)
    print json.dumps(data, sort_keys=True, indent=2)

