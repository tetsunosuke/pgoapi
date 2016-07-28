#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import time
import struct
import pprint
import logging
import requests
import argparse
import getpass
import traceback
import time

# add directory of this file to PATH, so that the package will be found
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# import Pokemon Go API lib
from pgoapi import pgoapi
from pgoapi import utilities as util

# other stuff
from google.protobuf.internal import encoder
from geopy.geocoders import GoogleV3
from s2sphere import Cell, CellId, LatLng
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

log = logging.getLogger(__name__)

def get_pos_by_name(location_name):
    geolocator = GoogleV3()
    loc = geolocator.geocode(location_name, timeout=10)
    if not loc:
        return None
    log.info('Your given location: %s', loc.address.encode('utf-8'))
    log.info('lat/long/alt: %s %s %s', loc.latitude, loc.longitude, loc.altitude)

    return (loc.latitude, loc.longitude, loc.altitude)

def get_cell_ids(lat, long, radius = 10):
    origin = CellId.from_lat_lng(LatLng.from_degrees(lat, long)).parent(15)
    walk = [origin.id()]
    right = origin.next()
    left = origin.prev()

    # Search around provided radius
    for i in range(radius):
        walk.append(right.id())
        walk.append(left.id())
        right = right.next()
        left = left.prev()

    # Return everything
    return sorted(walk)

def encode(cellid):
    output = []
    encoder._VarintEncoder()(output.append, cellid)
    return ''.join(output)

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
        13, # ビードル
        16, # ポッポ
        21, # オニスズメ
        41, # ズバット
        84, # ドードー
    ]
    return pokemon["pokemon_id"] in list

def weaker(pokemon):
    # Cpが一定以下はいらん
    return pokemon["cp"] < 150
    
    

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

    position = get_pos_by_name(config.location)
    if not position:
        log.error('Position could not be found by name')
        return
        
    if config.test:
        return

    # instantiate pgoapi
    api = pgoapi.PGoApi()
    if not api.login(config.auth_service, config.username, config.password):
        return

    api.get_inventory()

    # execute the RPC call
    response_dict = api.call()
    inventory_items =  response_dict["responses"]["GET_INVENTORY"]["inventory_delta"]["inventory_items"]
    my_pokemons = {}
    for item in inventory_items:
        try:
            if item["inventory_item_data"].has_key("pokemon_data"):
                pokemon_data = item["inventory_item_data"]["pokemon_data"]
                if pokemon_data.has_key("pokemon_id"):
                    log.debug("id=%s, name=%s, cp=%s", pokemon_data["pokemon_id"], poke_id2name(pokemon_data["pokemon_id"]), pokemon_data["cp"])
                    if my_pokemons.has_key(pokemon_data["pokemon_id"]):
                        my_pokemons[pokemon_data["pokemon_id"]].append(pokemon_data)
                    else:
                        my_pokemons[pokemon_data["pokemon_id"]] = [pokemon_data]
                    #if weaker(pokemon_data) or nomore(pokemon_data):
                    #    api.release_pokemon(pokemon_id = pokemon_data["id"])
                    #    dict = api.call()
                    #    time.sleep(3)
                      
        except:
            traceback.print_exc()
    log.info(my_pokemons)
if __name__ == '__main__':
    main()
