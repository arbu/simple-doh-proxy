import logging
import socket
from time import time
from select import select
from base64 import urlsafe_b64decode
from ipaddress import ip_address

try:
    from urllib.parse import parse_qsl
except ImportError:
    from urlparse import parse_qsl

class DefaultConfig(object):
    resolver = "::1"
    resolver_port = 53
    resolver_timeout = 1. # second(s)
    request_size_limit = 1000
    content_types = ["application/dns-message", # starting from draft 06
                     "application/dns-udpwireformat"] # until draft 04, still in use e.g. by firefox
    enforce_content_type = True

class Application(object):
    def __init__(self, config = None, logger = None):
        super(Application, self).__init__()
        self.config = config or DefaultConfig()
        self.logger = logger or logging.getLogger(__name__)

        addrinfo = socket.getaddrinfo(self.config.resolver, self.config.resolver_port, 0, socket.SOCK_DGRAM)[0]
        self.socket_params = addrinfo[:3]
        self.socket_dest = addrinfo[4]

    def __call__(self, environ, start_response):
        try:
            status, headers, answers = self.handle_request(environ)
        except Exception as e:
            status, headers, answers = self.error(environ, "500 Internal server error", internal = True)
        start_response(status, headers)
        return answers

    def error(self, environ, status, internal = False):
        remote = str(environ.get("REMOTE_ADDR", "<unknown>"))
        path = str(environ.get("PATH_INFO", ""))
        qs = str(environ.get("QUERY_STRING", ""))

        if internal:
            self.logger.error("An error occurred during the request from %s for %s?%s: %s",
                    remote, path, qs, status, exc_info = exc_info)
        else:
            self.logger.info("An error occurred during the request from %s for %s?%s: %s",
                    remote, path, qs, status)

        answer = status.encode("ascii")
        headers = [("Content-Length", str(len(answer))), ("Content-Type", "text/plain")]
        return status, headers, [answer]

    def handle_request(self, environ):
        params = dict(parse_qsl(environ.get("QUERY_STRING", ""), keep_blank_values = True))
        method = environ.get("REQUEST_METHOD", "UNKNOWN").upper()

        if method in ["GET", "HEAD"]:
            content_type = params.get("ct", self.config.content_types[0])

            try:
                query_b64 = params["dns"]
                query = urlsafe_b64decode(query_b64 + "=" * (-len(query_b64) % 4))
            except KeyError:
                return self.error(environ, "400 Missing parameter dns")
            except binascii.Error:
                return self.error(environ, "400 Invalid base64 encoding")

        elif method == "POST":
            length = int(environ.get("CONTENT_LENGTH", "0"))
            if self.config.request_size_limit and length > self.config.request_size_limit:
                return self.error(environ, "413 Request entity too large")

            query = environ["wsgi.input"].read(length)

            content_type = environ.get("CONTENT_TYPE", None)

        else:
            return self.error(environ, "501 Not implemented")

        if content_type not in self.config.content_types:
            if self.config.enforce_content_type:
                return self.error(environ, "415 Unsupported content type")
            content_type = self.config.content_types[0]

        try:
            response = self.dns_request(query)
        except TimeoutError as e:
            self.logger.warning("Resolver timed out: %s", e.args[0])
            return self.error(environ, "500 Resolver timed out")

        if method == "HEAD":
            response = b""

        return "200 Ok", [("Content-Length", str(len(response))), ("Content-Type", content_type)], [response]

    def dns_request(self, query):
        expiration = time() + self.config.resolver_timeout

        sock = socket.socket(*self.socket_params)
        try:
            sock.setblocking(0)

            # wait for socket being writable
            if select([], [sock], [sock], expiration - time()) == ([], [], []):
                raise TimeoutError("socket was not writable in time")

            sock.sendto(query, self.socket_dest)

            while expiration - time() > 0:
                # wait for socket being readable
                if select([sock], [], [sock], expiration - time()) == ([], [], []):
                    raise TimeoutError("recived no response in time")

                response, from_address = sock.recvfrom(65535)
                if ip_address(self.config.resolver) == ip_address(from_address[0]):
                    break
                else:
                    self.logger.warning("got response from %r but expected it from %r",
                            from_address, self.config.resolver)
            else:
                raise TimeoutError("recived no valid response in time")

        finally:
            sock.close()

        return response
