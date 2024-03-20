#!/usr/bin/env python3


class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def red(s):
    return Color.RED + str(s) + Color.END


def green(s):
    return Color.GREEN + str(s) + Color.END


def bold(s):
    return Color.BOLD + str(s) + Color.END


def RB(s):
    return bold(red(s))


def GB(s):
    return bold(green(s))


if __name__ == '__main__':
    print(Color.GB('Please run the following cmd to restore the extra dbs AFTER the K8s is running:'))
