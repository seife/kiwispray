# KIWIspray
# (C) 2019 SAP SE, Author: Stefan Seyfried
# License: GPL-2.0+, see COPYING

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, parse_qsl
from socketserver import ThreadingMixIn
import os
import sys
import logging

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
def respond_to_get_request(self, path):
    loc = self.request.getsockname()
    rem = self.request.getpeername()
    addrs = ({ 'ip': loc[0], 'port': loc[1] }, { 'ip': rem[0], 'port': rem[1] })
    logging.debug('>>>>Req->: %s', path)
    # logging.debug('>>>>Req->: %s', addrs)
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
        path = self.path
        data = respond_to_get_request(self, path)
        logging.debug("do_GET: data '%s'" % data)
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
def run_http(address = '', port = 5000):
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
    if known:
        if num == 0:
            return helpers.render_template('error.tmpl')
        state = host['state'].split(',')[0]
        hostdata['state'] = state
        logging.info("known host in state : %s" % state)
        # first look in ./<state>/host.tmpl...
        data = helpers.render_template('images/%s/host.tmpl' % state, replace = hostdata, failhard = True, templatedir = False)
        if data:
            return data
        # ...then look in templates/<state.tmpl>...
        data = helpers.render_template(state + '.tmpl', replace = hostdata, failhard = True)
        if data:
            return data
        # ...else return templates/known_host.tmpl
        return helpers.render_template('known_host.tmpl', replace = hostdata)
    return helpers.render_template('new_host.tmpl', replace = hostdata)

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

def list_hosts(args):
    fmt = "%4s %-20s %-10s %-s\n"
    hosts = helpers.get_hosts()
    data = fmt % ('#Id', 'Hostname', 'State', 'Serial#')
    for h in sorted(hosts, key=lambda k: k['id']):
        data += (fmt % (str(h['id']), h['hostname'], h['state'], h['serial']))
    return bytes(data, 'utf-8')
