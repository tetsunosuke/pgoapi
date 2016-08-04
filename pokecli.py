#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pgoapi - Pokemon Go API
Copyright (c) 2016 tjado <https://github.com/tejado>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
OR OTHER DEALINGS IN THE SOFTWARE.

Author: tjado <https://github.com/tejado>
"""

import os
import sys
import json
import time
import pprint
import logging
import getpass
import traceback
import requests
import time
import argparse

# add directory of this file to PATH, so that the package will be found
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util


log = logging.getLogger(__name__)

def init_config():
    parser = argparse.ArgumentParser()
    config_file = "config.json"

    # If config file exists, load variables from json
    load   = {}
    if os.path.isfile(config_file):
        with open(config_file) as data:
            load.update(json.load(data))

    # Read passed in Arguments
    required = lambda x: not x in load
    parser.add_argument("-a", "--auth_service", help="Auth Service ('ptc' or 'google')",
        required=required("auth_service"))
    parser.add_argument("-u", "--username", help="Username", required=required("username"))
    parser.add_argument("-p", "--password", help="Password")
    parser.add_argument("-l", "--location", help="Location", required=required("location"))
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true')
    parser.add_argument("-t", "--test", help="Only parse the specified location", action='store_true')
    parser.set_defaults(DEBUG=False, TEST=False)
    config = parser.parse_args()

    # Passed in arguments shoud trump
    for key in config.__dict__:
        if key in load and config.__dict__[key] == None:
            config.__dict__[key] = str(load[key])

    if config.__dict__["password"] is None:
        log.info("Secure Password Input (if there is no password prompt, use --password <pw>):")
        config.__dict__["password"] = getpass.getpass()

    if config.auth_service not in ['ptc', 'google']:
      log.error("Invalid Auth service specified! ('ptc' or 'google')")
      return None

    return config


def main():
    # log settings
    # log format
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    # log level for http request class
    logging.getLogger("requests").setLevel(logging.WARNING)
    # log level for main pgoapi class
    logging.getLogger("pgoapi").setLevel(logging.INFO)
    # log level for internal pgoapi class
    logging.getLogger("rpc_api").setLevel(logging.INFO)

    config = init_config()
    if not config:
        return

    if config.debug:
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("pgoapi").setLevel(logging.DEBUG)
        logging.getLogger("rpc_api").setLevel(logging.DEBUG)


    # instantiate pgoapi
    api = pgoapi.PGoApi()

    # parse position
    position = util.get_pos_by_name(config.location)
    if not position:
        log.error('Your given location could not be found by name')
        return
    elif config.test:
        return

    # set player position on the earth
    api.set_position(*position)

    if not api.login(config.auth_service, config.username, config.password, app_simulation = True):
        return

    # get player profile call (single command example)
    # ----------------------
    response_dict = api.get_player()
    print('Response dictionary (get_player): \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(response_dict)))

    # sleep due to server-side throttling
    time.sleep(0.2)

    # get player profile + inventory call (thread-safe/chaining example)
    # ----------------------
    req = api.create_request()
    req.get_player()
    req.get_inventory()
    response_dict = req.call()
    print('Response dictionary (get_player + get_inventory): \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(response_dict)))

def poke_id2name(id):
    url = "https://raw.githubusercontent.com/giginet/pokedex/master/dex/dex{0}.json".format(id)
    r = requests.get(url)
    """
    return {
        'image_url': "http://www.serebii.net/pokemongo/pokemon/{0:03d}.png".format(id),
        'name': r.json()['name']
    }
    """
    return r.json()["name"]

def nomore(pokemon):
    # 84: ドードー, 41: ズバット はもういらない
    list = [
        10, # キャタピー
        13, # ビードル
        16, # ポッポ
        17, # ピジョン
        19, # コラッタ
        21, # オニスズメ
        41, # ズバット
        69, # マダツボミ
        84, # ドードー
        85, # ドードリオ
        102, # タマタマ
        120, # ヒトデマン
    ]
    return pokemon["pokemon_id"] in list

def weaker(pokemon):
    # Cpが一定以下はいらん
    return pokemon["cp"] < 199
    
    
    
def my_main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
    # log level for http request class
    logging.getLogger("requests").setLevel(logging.WARNING)
    # log level for main pgoapi class
    logging.getLogger("pgoapi").setLevel(logging.INFO)
    # log level for internal pgoapi class
    logging.getLogger("rpc_api").setLevel(logging.INFO)

    config = init_config()
    if not config:
        return
    position = util.get_pos_by_name(config.location)
    if not position:
        log.error('Position could not be found by name')
        return
        
    if config.test:
        return

    # instantiate pgoapi
    api = pgoapi.PGoApi()
    api.set_position(*position)
    if not api.login(config.auth_service, config.username, config.password):
        return

    api.get_inventory()

    # execute the RPC call
    response_dict = api.call()
    with open("inventory.json", "w") as f:
        json.dump(response_dict,f, indent=4, sort_keys=True)
    inventory_items =  response_dict["responses"]["GET_INVENTORY"]["inventory_delta"]["inventory_items"]
    my_pokemons = {}
    for item in inventory_items:
        try:
            if item["inventory_item_data"].has_key("pokemon_data"):
                pokemon_data = item["inventory_item_data"]["pokemon_data"]
                if pokemon_data.has_key("pokemon_id"):
                    #log.debug("id=%s, name=%s, cp=%s", pokemon_data["pokemon_id"], poke_id2name(pokemon_data["pokemon_id"]), pokemon_data["cp"])
                    if my_pokemons.has_key(pokemon_data["pokemon_id"]):
                        my_pokemons[pokemon_data["pokemon_id"]].append(pokemon_data)
                    else:
                        my_pokemons[pokemon_data["pokemon_id"]] = [pokemon_data]
                      
        except:
            traceback.print_exc()
    #log.info(my_pokemons)
    with open("pokemons.json", "w") as f:
        json.dump(my_pokemons,f, indent=4, sort_keys=True)

    # 保持しているデータを処理
    for id in my_pokemons:
        owns = my_pokemons[id]
        for pokemon in owns:
            if pokemon.has_key("favorite"):
                log.debug(poke_id2name(id))
                continue
            if weaker(pokemon) or nomore(pokemon):
                api.release_pokemon(pokemon_id = pokemon["id"])
                dict = api.call()
                time.sleep(3)


if __name__ == '__main__':
    #main()
    my_main()
