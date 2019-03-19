# KIWIspray
# (C) 2019 SAP SE, Author: Stefan Seyfried
# License: GPL-2.0+, see COPYING

import json
import threading
import os
import sys
import logging
import uuid

lock = threading.Lock()

def load_json(filename):
    try:
        with open(filename, 'r') as json_file:
            data = json.load(json_file)
            json_file.close()
            return data
    except:
        return []

def save_json(filename, hosts):
    with open(filename, 'w') as json_file:
        json.dump(hosts, json_file, indent = 4, sort_keys = True)

def find_one(stack, key, what):
    found = 0
    ids = []
    for host in stack:
        if host[key] == what:
            ids.append(host['id'])
            found += 1
    return found, ids

def find_mac(stack, mac):
    found = 0
    ids = []
    for host in stack:
        for macs in host['macs'].split():
            if macs == mac:
                ids.append(host['id'])
                found += 1
                break
    return found, ids

def find_host_by_id(arg):
    lock.acquire()
    known_hosts = load_json('known_hosts.json')
    logging.debug("find_host_by_id arg %d\n%s", arg, known_hosts)
    host = list(filter(lambda host: host['id'] == arg, known_hosts))
    lock.release()
    if host:
        return host[0]
    return None

def get_hosts():
    lock.acquire()
    known_hosts = load_json('known_hosts.json')
    lock.release()
    return known_hosts

def find_host(args, new_bootid = False):
    known = False
    error = False
    hostid = 0
    lock.acquire()
    tmph = { 'macs': '', 'serial': '', 'uuid': '', 'hostname': 'not-set', 'metadata': { } }
    for key in args:
        arg = args[key]
        logging.debug("find_host key %s %s", key, arg)
        try:
            arg = arg.upper()
        except:
            pass # numbers...
        if not arg:
            logging.debug("%s empty" % key)
            continue
        if key.startswith('net'):
            if tmph['macs']:
                tmph['macs'] += ' '
            tmph['macs'] += arg.replace('-', ':')
        elif key == 'serial':
            tmph['serial'] = arg
        elif key == 'uuid':
            tmph['uuid'] = arg
    logging.debug(tmph)
    known_hosts = load_json('known_hosts.json')
    for key in ['serial', 'uuid']:
        if not tmph[key]:
            continue
        (found, ids) = find_one(known_hosts, key, tmph[key])
        if found > 1:
            error = True
        elif found > 0:
            if known:
                if hostid != ids[0]:
                    error = True
            else:
                known = True
                hostid = ids[0]
        logging.debug("found %s %s %d times", key, tmph[key], found)
    for mac in tmph['macs'].split():
        (found, ids) = find_mac(known_hosts, mac)
        if found > 1:
            error = True
        elif found > 0:
            if known:
                if hostid != ids[0]:
                    error = True
            else:
                known = True
                hostid = ids[0]
        logging.debug("found mac %s %d times", mac, found)
    #print(known_hosts)
    if error:
        lock.release()
        return known, 0, None
    if new_bootid:
        bootid = uuid.uuid1().hex
        tmph['bootid'] = bootid
    if not known:
        ids = sorted([d['id'] for d in known_hosts if 'id' in d])
        if ids:
            id = ids[-1]
        else:
            id = 0
        id = int(id) + 1
        logging.info("new host with id: %d", id)
        if tmph['serial'] and tmph['macs']:
            tmph['id'] = id
            tmph['state'] = 'new'
            known_hosts.append(tmph)
            save_json('known_hosts.json', known_hosts)
            lock.release()
            return known, ids, tmph
    host = list(filter(lambda host: host['id'] == hostid, known_hosts))[0]
    #print ("host found:", host)
    if new_bootid:
        host['bootid'] = bootid
        save_json('known_hosts.json', known_hosts)
    lock.release()
    return known, hostid, host

def read_bin_file(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'rb') as file:
            data = file.read()
            file.close()
        return(data)
    return None

#-------
# simple template render function, replace = { 'FOO': 'bar', 'BAZ': 'boom' }
# replaces '@FOO@' with 'bar' and '@BAZ@' with 'boom'
def render_template(name, replace = {}, failhard = False, templatedir = True):
    path = os.path.dirname(sys.argv[0])
    if templatedir:
        path += '/templates'
    data = read_bin_file(path + '/' + name)
    logging.info("render_template name: '%s'", name)
    if data:
        logging.debug("render_template replace: '%s'", replace)
        for ss in replace:
            s = bytes('@' + ss + '@', 'utf-8')
            r = bytes(str(replace[ss]), 'utf-8')
            data = data.replace(s, r)
        if 'metadata' in replace:
            md = replace['metadata']
            for ss in md:
                s = bytes('@metadata.' + ss + '@', 'utf-8')
                r = bytes(str(md[ss]), 'utf-8')
                data = data.replace(s, r)
        return bytes(data)
    if failhard:
        return None
    return bytes('unknown template %s\n\n' % name, 'utf-8')

def transition(id, state = None, hostname = None, metadata = None, bootid = None):
    lock.acquire()
    known_hosts = load_json('known_hosts.json')
    for host in known_hosts:
        if host['id'] == id:
            if bootid:
                if not 'bootid' in host:
                    logging.warning("transition called with bootid %s, but host has no bootid", bootid)
                    lock.release()
                    return False
                if bootid != host['bootid']:
                    logging.warning("transition called with wrong bootid %s, correct %s" , bootid, host['bootid'])
                    lock.release()
                    return False
            if state:
                if state == 'finished' and bootid:              # special case, only if called via http API:
                    try:                                        # if multiple states are specified 'foo,bar,baz'
                       state = host['state'].split(',', 1)[1]   # remove the first word from comma separated list
                       logging.info("transitioned host to next state %s", state)
                    except:
                       pass
                host['state'] = state
            if hostname:
                host['hostname'] = hostname
            if metadata:
                host['metadata'] = metadata
            save_json('known_hosts.json', known_hosts)
            lock.release()
            return True
    lock.release()
    return False
