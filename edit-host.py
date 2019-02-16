#!/usr/bin/python3
# KIWIspray
# (C) 2019 SAP SE, Author: Stefan Seyfried
# License: GPL-2.0+, see COPYING

import KS.helpers as helpers
import argparse
import json
from sys import exit

def list_hosts(id = None):
    fmt= "%4s %-20s %-10s %-s"
    known_hosts = helpers.load_json('known_hosts.json')
    #print(known_hosts)
    print(fmt % ('#Id', 'Hostname', 'State', 'Serial#'))
    for h in sorted(known_hosts, key=lambda k: k['id']):
        if id and h['id'] != id:
            continue
        print(fmt % (str(h['id']), h['hostname'], h['state'], h['serial']))
        if id and h['metadata']:
            print("     Metadata:")
            m = h['metadata']
            for i in sorted(m):
                print("        %-10s %-s" % (i, m[i]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Set host state / metadata')
    parser.add_argument('-i', '--id', type=int, help='host ID number')
    parser.add_argument('-l', '--list', help='List known hosts', action='store_true')
    parser.add_argument('-s', '--state', help='State to transition the host to')
    parser.add_argument('-m', '--meta', help='JSON metadata to attach to the host')
    parser.add_argument('-n', '--hostname', help='Host name for host[id]')
    args = parser.parse_args()
    if args.list:
        list_hosts(args.id)
        exit(0)
    if args.id:
        if args.meta:
            meta = json.loads(args.meta)
        else:
            meta = None
        if helpers.transition(args.id, state = args.state, hostname = args.hostname, metadata = meta):
            list_hosts(args.id)
            exit(0)
        else:
            print("an error occured :-(")
            exit(1)
    print("need at least ID and state...")
    exit(2)
