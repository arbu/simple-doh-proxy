Simple DOH Proxy
================

This is a rather simple WSGI compatible implementation of 
a [DNS-over-HTTPS](https://tools.ietf.org/html/draft-ietf-doh-dns-over-https-13) 
proxy. It only supports the DNS wire format (application/dns-message) and has 
no support for cache control headers.

Running
-------

Adjust doh_wsgi.py to your needs or create your own wsgi application file.

For python 2 you need to install `py2-ipaddress`.

```
uwsgi --module doh_wsgi --http-socket :8080
```

the following should show a 200 status code:

```
curl -v http://localhost:8080/\?dns\=AAABAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB
```

to examine the response message use:

```
curl http://localhost:8080/\?dns\=AAABAAABAAAAAAAAA3d3dwdleGFtcGxlA2NvbQAAAQAB | python3 -c 'import sys,dns.message; print(dns.message.from_wire(sys.stdin.buffer.read()).to_text())'
```


Security
--------

Beware that this proxy will forward any kind of DNS query from the IP address
of the proxy. If you have access control based on IP addresses in place you
should keep this in mind.
