# encoding: utf-8
from datetime import datetime, tzinfo, timedelta
import os
import re

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


def is_below_v3_9(ver):
    # 对于 master 版本，不做校验；对于 v3.6.x、v3.7.x这样的格式，做版本校验
    if ver.startswith('master-'):
        return False
    segs = ver.split('.')
    v_1st = int(segs[0].strip('v'))
    v_2nd = int(segs[1])
    if v_1st > 3:
        return False
    elif v_1st < 3:
        return True
    else:
        if v_2nd < 9:
            return True
    return False


def to_yaml(data):
    import yaml
    return yaml.dump(data, default_flow_style=False)

def print_title(title):
    print('\n')
    print('=' * 80)
    print(title)
    print('=' * 80)


def init_local_user_path():
    import os
    path = os.environ['PATH']
    user_bin = os.path.expanduser('~/.local/bin')
    if user_bin not in path.split(os.pathsep):
        path = f'{path}:{user_bin}'
        os.environ['PATH'] = path


def prRed(skk):
    print("\033[31m{}\033[00m" .format(skk))


def tryBackupFile(filename):
    # only for no write access
    if not os.path.exists(filename):
        return
    if os.access(filename, os.W_OK):
        return

    date = datetime.now().strftime('%Y%m%d')
    new_path = f'{filename}.{date}'
    os.system(f'sudo mv {filename} {new_path}')

# simply search for regex match
def regex_search(pattern, string, ignore_case=False):
    flags = re.IGNORECASE if ignore_case else 0
    match = re.search(pattern, string, flags)
    if match:
        return match.group(0)
    return None
