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
import pprint
import logging
import argparse
import getpass
import traceback
import requests
import time

# add directory of this file to PATH, so that the package will be found
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util


log = logging.getLogger(__name__)

def init_config():
    parser = argparse.ArgumentParser()
    config_file = "config_bot.json"
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

    position = util.get_pos_by_name(config.location)
    if not position:
        log.error('Your given location could not be found by name')
        return

    if config.test:
        return

    # instantiate pgoapi
    api = pgoapi.PGoApi()

    # provide player position on the earth
    api.set_position(*position)

    if not api.login(config.auth_service, config.username, config.password):
        return

    # chain subrequests (methods) into one RPC call

    # get player profile call
    # ----------------------
    #api.get_player()

    # get inventory call
    # ----------------------
    #api.get_inventory()

    # get map objects call
    # repeated fields (e.g. cell_id and since_timestamp_ms in get_map_objects) can be provided over a list
    # ----------------------
    cell_ids = util.get_cell_ids(position[0], position[1])
    timestamps = [0,] * len(cell_ids)
    api.get_map_objects(latitude = position[0], longitude = position[1], since_timestamp_ms = timestamps, cell_id = cell_ids)
    response_dict = api.call()
    fort = response_dict["responses"]["GET_MAP_OBJECTS"]["map_cells"][0]["forts"][0]

    # spin a fort
    # ----------------------
    #fortid = '<your fortid>'
    #lng = <your longitude>
    #lat = <your latitude>
    #api.fort_search(fort_id=fortid, fort_latitude=lat, fort_longitude=lng, player_latitude=f2i(position[0]), player_longitude=f2i(position[1]))
    if fort["enabled"]:
        fortid = fort["id"]
        lng = fort["longitude"]
        lat = fort["latitude"]
        api.fort_details(fort_id=fortid, latitude=lat, longitude=lng)
        #, player_latitude=util.f2i(position[0]), player_longitude=util.f2i(position[1]))
        response_dict = api.call()
        detailed = response_dict["responses"]["FORT_DETAILS"]
        api.fort_search(fort_id=detailed["fort_id"], fort_latitude=detailed["latitude"], fort_longitude=detailed["longitude"], player_latitude=util.f2i(position[0]), player_longitude=util.f2i(position[1]))
        time.sleep(1)
        response_dict = api.call()
        with open("result.json", "w") as f:
            json.dump(response_dict,f, indent=4, sort_keys=True)

    # release/transfer a pokemon and get candy for it
    # ----------------------
    #api.release_pokemon(pokemon_id = <your pokemonid>)

    # evolve a pokemon if you have enough candies
    # ----------------------
    #api.evolve_pokemon(pokemon_id = <your pokemonid>)

    # get download settings call
    # ----------------------
    #api.download_settings(hash="05daf51635c82611d1aac95c0b051d3ec088a930")

    # execute the RPC call
    #response_dict = api.call()

    # print the response dict
    #print('Response dictionary: \n\r{}'.format(pprint.PrettyPrinter(indent=4).pformat(response_dict)))

    # or dumps it as a JSON
    #print('Response dictionary: \n\r{}'.format(json.dumps(response_dict, indent=2, cls=util.JSONByteEncoder)))

    # alternative:
    # api.get_player().get_inventory().get_map_objects().download_settings(hash="05daf51635c82611d1aac95c0b051d3ec088a930").call()

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
    with open("response.json", "w") as f:
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
        json.dump(my_pokemons,f) 

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
    main()
    #my_main()
