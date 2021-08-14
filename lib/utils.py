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
    # 对于 master 版本，不做校验；对于 v3.6.x、v3.7.x这样的格式，做版本校验
    if ver.startswith('master-'):
        return 'master'

    if (not ver.startswith('master-')) and len(segs) < 3:
        raise Exception("Invalid version %s", ver)
    return '%s_%s' % (segs[0], segs[1])


def to_yaml(data):
    return yaml.dump(data, default_flow_style=False)

def animated_waiting(func_name, *args, **kwargs):
    import itertools
    import threading
    import time
    import sys
    done = False

    def animate():
        for c in itertools.cycle(['|', '/', '-', '\\']):
            if done:
                break
            sys.stdout.write('\rPlease wait... ' + c)
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.flush()
        sys.stdout.write('\rDone!            \n')

    t = threading.Thread(target=animate)
    t.start()

    func_name(*args, **kwargs)

    done = True
    print('\n')
