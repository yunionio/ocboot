from lib.service import ClickhouseService


def add_command(subparsers):
    ClickhouseService(subparsers, 'clickhouse')
