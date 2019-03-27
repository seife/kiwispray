#!/usr/bin/python3
#
# KIWIspray
# (C) 2019 SAP SE, Author: Stefan Seyfried
# License: GPL-2.0+, see COPYING

import logging
import os
import sys
import KS

def main(discover):
    path = os.path.dirname(sys.argv[0])
    if path:
        os.chdir(path)
    KS.run(discover)

if __name__ == "__main__":
    if '-d' in sys.argv:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    if '--discover' in sys.argv:
        discover = True
    else:
        discover = False
    main(discover)
