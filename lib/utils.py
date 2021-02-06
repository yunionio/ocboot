# encoding: utf-8
from datetime import datetime, tzinfo, timedelta

import yaml


def ensure_ascii(s):
    if not isinstance(s, str):
        s = '%s' % s
    if isinstance(s, str):
        return s
    else:
        return s.encode('utf-8')


def td_total_seconds(td):
    return td.days*86400 + td.seconds


def parse_isotime(expires):
    return datetime.strptime(expires+"UTC", '%Y-%m-%dT%H:%M:%S.%fZ%Z')


class simple_utc(tzinfo):

    def tzname(self, **kwargs):
        return 'UTC'

    def utcoffset(self, dt):
        return timedelta(0)


def parse_k8s_time(time_str):
    # time_str: e.g., 2021-02-03T11:33:05Z
    ret = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
    return ret.replace(tzinfo=simple_utc())


def get_major_version(ver):
    segs = ver.split('.')
    if len(segs) < 3:
        raise Exception("Invalid version %s", ver)
    return '%s_%s' % (segs[0], segs[1])


def to_yaml(data):
    return yaml.dump(data)
