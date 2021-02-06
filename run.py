#!/usr/bin/env python

import sys

from lib import install


def show_usage():
    usage = '''
Usage: %s <config_file>.yml
''' % __file__
    print(usage)


def main():
    if len(sys.argv) != 2:
        show_usage()
        sys.exit(1)
    return install.start(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
