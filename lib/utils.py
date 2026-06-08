# encoding: utf-8
from datetime import datetime, tzinfo, timedelta
import ipaddress
import os
import re
import socket


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
    if ver.startswith('master'):
        return 'master'

    if (not ver.startswith('master-')) and len(segs) < 3:
        raise Exception("Invalid version %s", ver)
    return '%s_%s' % (segs[0], segs[1])


def is_below_v3_9(ver):
    # 对于 master 版本，不做校验；对于 v3.6.x、v3.7.x这样的格式，做版本校验
    if ver.startswith('master'):
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


def pr_red(*skk):
    print("\033[31m{}\033[00m" .format(' '.join(skk)))


def pr_green(skk):
    print("\033[1m\033[92m{}\033[00m" .format(skk))


def regex_search(pattern, string, ignore_case=False):
    flags = re.IGNORECASE if ignore_case else 0
    match = re.search(pattern, string, flags)
    if match:
        return match.group(0)
    return None

def is_valid_dns(dns):
    try:
        socket.gethostbyname(dns)
        return True
    except socket.gaierror:
        return False

def generage_random_string(N=12):
    import random
    import string
    return ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in range(N))

def is_ipv4(addr):
    try:
        socket.inet_pton(socket.AF_INET, addr)
        return True
    except (OSError, AttributeError, socket.error):
        return False

def is_ipv6(addr):
    try:
        socket.inet_pton(socket.AF_INET6, addr)
        return True
    except (OSError, AttributeError, socket.error):
        return False


def parse_ip(addr):
    if not addr or addr == '127.0.0.1':
        return None
    try:
        return ipaddress.ip_address(addr)
    except ValueError:
        return None


def ip_in_cidr(ip_str, cidr_str):
    ip = parse_ip(ip_str)
    if ip is None:
        return False
    try:
        network = ipaddress.ip_network(cidr_str, strict=False)
    except ValueError as e:
        raise Exception("Invalid CIDR format: %s" % cidr_str) from e
    if ip.version != network.version:
        return False
    return ip in network


def check_ips_against_cidrs(ips, cidrs):
    errors = []
    for label, ip_str in ips:
        ip = parse_ip(ip_str)
        if ip is None:
            continue
        for cidr_name, cidr_str in cidrs:
            try:
                network = ipaddress.ip_network(cidr_str, strict=False)
            except ValueError:
                raise Exception("Invalid CIDR format: %s" % cidr_str)
            if ip.version != network.version:
                continue
            if ip in network:
                errors.append(
                    "Node IP %s (%s) conflicts with %s %s" % (
                        ip_str, label, cidr_name, cidr_str))
    return errors


def parse_k3s_network_cidrs(config_yaml):
    import yaml
    try:
        data = yaml.safe_load(config_yaml) or {}
    except yaml.YAMLError as e:
        raise Exception("Failed to parse k3s config.yaml: %s" % e) from e

    cidrs = []
    cluster_cidr = data.get('cluster-cidr')
    service_cidr = data.get('service-cidr')

    if cluster_cidr:
        for part in str(cluster_cidr).split(','):
            part = part.strip()
            if part:
                cidrs.append(('pod_network_cidr', part))

    if service_cidr:
        for part in str(service_cidr).split(','):
            part = part.strip()
            if part:
                cidrs.append(('service_cidr', part))

    return cidrs


def validate_cidr(cidr_str, name, version=None):
    try:
        network = ipaddress.ip_network(cidr_str, strict=False)
    except ValueError as e:
        raise Exception("Invalid %s CIDR format: %s" % (name, cidr_str)) from e
    if version is not None and network.version != version:
        raise Exception("%s must be IPv%d CIDR, got: %s" % (name, version, cidr_str))
    return str(network)


def apply_cidr_to_config_dict(config_dict, ip_type=None, pod_network_cidr=None,
                              service_cidr=None, pod_network_cidr_v4=None,
                              service_cidr_v4=None):
    changed = False

    if pod_network_cidr is not None:
        config_dict['pod_network_cidr'] = pod_network_cidr
        changed = True
    if service_cidr is not None:
        config_dict['service_cidr'] = service_cidr
        changed = True
    if pod_network_cidr_v4 is not None:
        config_dict['pod_network_cidr_v4'] = pod_network_cidr_v4
        changed = True
    if service_cidr_v4 is not None:
        config_dict['service_cidr_v4'] = service_cidr_v4
        changed = True

    if ip_type == 'ipv4':
        if pod_network_cidr_v4 is not None:
            config_dict['pod_network_cidr'] = pod_network_cidr_v4
            changed = True
        if service_cidr_v4 is not None:
            config_dict['service_cidr'] = service_cidr_v4
            changed = True

    return changed
