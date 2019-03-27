# KIWIspray
# (C) 2019 SAP SE, Author: Stefan Seyfried
# License: GPL-2.0+, see COPYING

from http.server import BaseHTTPRequestHandler, HTTPServer
from cgi import parse_header, parse_multipart
from urllib.parse import parse_qs, parse_qsl
from socketserver import ThreadingMixIn
import os
import sys
import logging
import json

import KS.helpers as helpers

# set headers etc. for generated plain text, rather short "files"
def send_back(self, data, code = 200):
    self._set_headers(size = len(data), ctype = 'text/plain', code = code)
    return data

# get args from URL path, sanitize id and bootid
def get_args(path):
    args = {}
    if '?' in path:
        (path, argstr) = path.split("?", 1)
        args = dict(parse_qsl(argstr))
    # these two are wanted by many functions, sanitize to avoid checking everywhere
    try:
        tmp = int(args['id'])
        args['id'] = tmp
    except:
        args['id'] = 0
    if not 'bootid' in args:
        args['bootid'] = 'none_given' # invalid
    return args, path

#------------------------------------------------------------------------------#
#                       handle http get request                                #
#------------------------------------------------------------------------------#
def respond_to_get_request(self):
    loc = self.request.getsockname()
    rem = self.request.getpeername()
    addrs = ({ 'ip': loc[0], 'port': loc[1] }, { 'ip': rem[0], 'port': rem[1] })
    args, path = get_args(self.path)
    logging.info("path: %s args: %s", path, args)
    if path == '/bootstrap':
        data = bootme(args, addrs)
        return send_back(self, data)
    elif path == '/post-install':
        data, status = post_install(args, addrs)
        return send_back(self, data, status)
    elif path == '/finish':
        data, status = finish(args, addrs)
        return send_back(self, data, status)
    elif path == '/state':
        data, status = get_state(args)
        return send_back(self, data, status)
    elif path == '/hosts':
        data = list_hosts(args)
        return send_back(self, data)
    # else
    file_name = path.lstrip('/')
    if os.path.exists(file_name):
        size = os.path.getsize(file_name)
        self._set_headers(size)
        with open(file_name, 'rb') as f:
            while True:
                buf = f.read(8192)
                if buf:
                    self.wfile.write(buf)
                else:
                    break
            f.close()
        return None
    lip = addrs[0]
    replace = { 'SERVER_IP': lip['ip'], 'SERVER_PORT': lip['port'] }
    data = helpers.render_template(file_name, replace, True)
    if data:
        return send_back(self, data)
    return send_back(self, bytes('file not found\n', 'utf-8'), 404)

def respond_to_post_request(self):
    args, path = get_args(self.path)
    logging.info('post path: %s args: %s', path, args)
    try:
        ctype, pdict = parse_header(self.headers['content-type'])
    except:
        ctype = ''
        pdict = {}
    if ctype == 'multipart/form-data':
        post_data = parse_multipart(self.rfile, pdict)
    elif ctype == 'application/x-www-form-urlencoded':
        length = int(self.headers['content-length'])
        post_decoded = self.rfile.read(length).decode('utf-8')
        post_data = parse_qs(post_decoded, keep_blank_values=1, encoding="utf-8", errors="strict")
    else:
        post_data = {}
    if path == '/update':
        data, status = update_host(args, post_data)
        return send_back(self, data, status)
    return send_back(self, bytes('bad request\n', 'utf-8'), 400)

#------------------------------------------------------------------------------#
#           http request handler                                               #
#------------------------------------------------------------------------------#
class Server(BaseHTTPRequestHandler):
    def _set_headers(self, size = 0, ctype = None, code = 200):
        self.send_response(code)
        path = self.path
        if ctype:
            self.send_header('content-type', ctype)
        elif '.css' in path:
            self.send_header('Content-type', 'text/css')
        elif '.html' in path:
            self.send_header('Content-type', 'text/html')
        else:
            self.send_header('Content-Type', 'application/octet-stream')
        if size:
            self.send_header('Content-Length', size)
        self.end_headers()
    # process get requests
    def do_GET(self):
        data = respond_to_get_request(self)
        logging.debug("do_GET: data '%s'" % data)
        if data:
            self.wfile.write(data)
    def do_POST(self):
        # print(self.headers)
        data = respond_to_post_request(self)
        if data:
            self.wfile.write(data)
    # send headder
    def do_HEAD(self):
        self._set_headers()
    def log_message(self, format, *args):
        return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thraed."""

#------------------------------------------------------------------------------#
#           run the http server in backgroung                                  #
#------------------------------------------------------------------------------#
def run_http(discover = False, address = '', port = 5000):
    helpers.set_discover(discover)
    server_class=ThreadedHTTPServer
    handler_class=Server
    server_address = (address, port)
    httpd = server_class(server_address, handler_class)
    print('starting http server at port',  port)
    #http_thread = threading.Thread(target = httpd.serve_forever, args=())
    #http_thread.daemon = True
    #http_thread.start()
    httpd.serve_forever()

def bootme(args, addrs):
    logging.debug("bootme: %s" % args)
    known, num, host = helpers.find_host(args, True)
    logging.debug("known, num: %s, %s", known, num)
    lip = addrs[0]
    hostdata = { 'HOST_DATA': 'unknown', 'HOST': num, 'SERVER_IP': lip['ip'], 'SERVER_PORT': lip['port'] }
    if host:
        hostdata.update(host)
        hostdata['HOST_DATA'] = ''
        for key in sorted(host):
            hostdata['HOST_DATA'] += 'echo * '+ key + ': "' + str(host[key]) + '"\n'
    if num == 0:
        return helpers.render_template('error.tmpl')
    state = host['state'].split(',')[0]
    hostdata['state'] = state
    logging.info("found host in state : %s" % state)
    # first look in ./<state>/host.tmpl...
    data = helpers.render_template('images/%s/host.tmpl' % state, replace = hostdata, failhard = True, templatedir = False)
    if data:
        return data
    # ...then look in templates/<state.tmpl>...
    data = helpers.render_template(state + '.tmpl', replace = hostdata, failhard = True)
    if data:
        return data
    # ...else return templates/known_host.tmpl
    # something went wrong? No matching state?
    return helpers.render_template('known_host.tmpl', replace = hostdata)

def post_install(args, addrs):
    logging.debug("post_install: %s" % args)
    id = args['id']
    if id == 0:
        logging.warning("post_install: no ID")
        return bytes('invalid query, no id\n\n', 'utf-8'), 404
    host = helpers.find_host_by_id(id)
    if host['bootid'] != args['bootid']:
        logging.warning("post_install: given bootid '%s' is wrong (%s)", args['bootid'], host['bootid'])
        return bytes('invalid bootid\n\n', 'utf-8'), 401
    lip = addrs[0]
    hostdata = { 'HOST': id, 'SERVER_IP': lip['ip'], 'SERVER_PORT': lip['port'] }
    if host:
        hostdata.update(host)
        state = host['state'].split(',')[0]
        hostdata['state'] = state
        data = helpers.render_template('images/%s/post_install.tmpl' % state, replace = hostdata, failhard = True, templatedir = False)
        if data:
            return data, 200
        return helpers.render_template('post_install.tmpl', replace = hostdata), 200
    return bytes('host %s not found\n\n' % id, 'utf-8'), 404

def update_host(args, post_data):
    logging.debug("update_host %s" % args)
    id = args['id']
    if id == 0:
        logging.warning("update_host: no ID")
        return bytes('invalid query, no id\n\n', 'utf-8'), 404
    host = helpers.find_host_by_id(id)
    if not host:
        return bytes('host %s not found\n\n' % id, 'utf-8'), 404
    if not host['bootid'] or host['bootid'] != args['bootid']:
        logging.warning("update_host: given bootid '%s' is wrong (%s)", args['bootid'], host['bootid'])
        return bytes('invalid bootid\n\n', 'utf-8'), 401
    state = host['state'].split(',')[0]
    if state != 'discover':
        logging.warning("update_host: state of host %d is not discover (%s)", id, host['state'])
        return bytes('invalid state\n\n', 'utf-8'), 401
    macs = host['macs']
    metadata = host['metadata']
    for k in post_data:
        v = post_data[k]
        for l in v:
            if k == 'mac':
                try:
                    mac = l.upper()
                except:
                    continue
                if mac in macs:
                    continue
                macs += ' ' + mac
                continue
            if k == 'metadata':
                try:
                    meta = json.loads(l)
                except Exception as e:
                    print(e)
                    continue
                metadata.update(meta)
                continue
            logging.error("update_host: unhandled post_data key %s", k)
            return bytes('unhandled post_data key\n', 'utf-8'), 400
    hostdata = {}
    hostdata['macs'] = macs
    hostdata['metadata'] = metadata
    if helpers.update_hostdata(id, hostdata):
        return bytes('ok\n', 'utf-8'), 200
    return bytes('an error occured\n', 'utf-8'), 500

def finish(args, addrs):
    logging.debug("finish: args '%s'", args)
    id = args['id']
    bi = args['bootid']
    if id == 0:
        logging.warning("finish: no ID")
        return bytes('invalid query, no id\n\n', 'utf-8'), 404
    if helpers.transition(id, state = 'finished', bootid = bi):
        logging.info("finish: id %d success", id)
        return bytes('host %s successfully transitioned to finished state\n\n' %id, 'utf-8'), 200
    return bytes('host %s not found or bootid %s invalid\n\n' % (id, bi), 'utf-8'), 401

def get_state(args):
    logging.debug("get_state: args '%s'", args)
    id = args['id']
    if id == 0:
        logging.warning("get_state: no ID")
        return bytes('invalid query, no id\n\n', 'utf-8'), 404
    host = helpers.find_host_by_id(id)
    if not host:
        return bytes('host %s not found\n\n' % id, 'utf-8'), 404
    state = host['state'].split(',')[0]
    return bytes('%s\n' % state, 'utf-8'), 200

def list_hosts(args):
    fmt = "%4s %-20s %-10s %-s\n"
    hosts = helpers.get_hosts()
    data = fmt % ('#Id', 'Hostname', 'State', 'Serial#')
    for h in sorted(hosts, key=lambda k: k['id']):
        data += (fmt % (str(h['id']), h['hostname'], h['state'], h['serial']))
    return bytes(data, 'utf-8')
