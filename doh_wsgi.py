import logging
from simple_doh_proxy import Application, DefaultConfig

logger = logging.getLogger("simple_doh_proxy")
logger.setLevel(logging.DEBUG)

# Uncomment this to log into a file
#logFile = logging.FileHandler("/var/log/simple-doh-proxy.log")
#logFile.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
#logger.addHandler(logFile)

class Config(DefaultConfig):
    resolver = "2001:4f8:0:2::14"
    # check simple_doh_proxy.py for all options and defaults

application = Application(Config(), logger)
