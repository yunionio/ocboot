import random
from datetime import datetime

from lib import utils


class TenantInfoManager(object):

    def __init__(self):
        self.tenants = {}

    def add_tenant(self, tenant):
        self.tenants[tenant.get_id()] = tenant

    def remove_tenant(self, tenant):
        del self.tenants[tenant.get_id()]

    def get_tenants(self):
        tenants = []
        for v in list(self.tenants.values()):
            tenants.append({'id': v.get_id(), 'name': v.get_name()})
        return tenants

    def get_tenant(self, tenant_name=None, tenant_id=None):
        for t in list(self.tenants.values()):
            if tenant_id is not None and len(tenant_id) > 0:
                if t.get_id() == tenant_id and not t.expire_soon():
                    return t
            elif tenant_name is not None and len(tenant_name) > 0:
                if t.get_name() == tenant_name and not t.expire_soon():
                    return t
        return None

    def from_json(self, desc):
        for tdesc in desc:
            t = TenantInfo(None, None)
            t.from_json(tdesc)
            self.add_tenant(t)

    def to_json(self):
        desc = []
        for t in list(self.tenants.values()):
            desc.append(t.to_json())
        return desc


class TenantInfo(object):

    def __init__(self, idstr, name):
        self.__id = idstr
        self.__name = name
        self.token = None
        self.catalog = None
        self.user = None

    def set_access_info(self, token, catalog, user, no_check=False):
        self.start_time = datetime.utcnow()
        self.token   = token
        self.catalog = catalog
        self.user = user
        if not no_check:
            diff = self.get_expire() - self.start_time
            if utils.td_total_seconds(diff) <= 60:
                raise Exception('Incorrect system time')

    def get_id(self):
        if self.__id is None and self.token is not None:
            self.__id = self.token['tenant']['id']
        return self.__id

    def get_name(self):
        if self.__name is None and self.token is not None:
            self.__name = self.token['tenant']['name']
        return self.__name

    def get_expire(self):
        if self.token:
            return utils.parse_isotime(self.token['expires'])
        else:
            return None

    def expire_soon(self):
        if self.token is None:
            return True
        expire = self.get_expire()
        utcnow = datetime.utcnow()
        if expire <= utcnow:
            return True
        nowdiff = expire - utcnow
        if expire <= self.start_time:
            return True
        diff = expire - self.start_time
        if utils.td_total_seconds(nowdiff) < utils.td_total_seconds(diff)/2:
            return True
        return False

    def get_token(self):
        if self.token:
            return self.token['id']
        else:
            return None

    def get_regions(self):
        if self.catalog is None:
            return None
        return self.get_regions_v3()

    def get_regions_v3(self):
        regions = {}
        for service in self.catalog:
            if service['type'] != 'compute':
                continue
            for endpoint in service['endpoints']:
                region = endpoint['region_id']
                if region not in regions:
                    regions[region] = {}
                if endpoint['interface'] == 'public':
                    regions[region]['publicURL'] = endpoint['url']
                elif endpoint['interface'] == 'internal':
                    regions[region]['internalURL'] = endpoint['url']
        ret = []
        for region, urls in regions.items():
            urls['region'] = region
            ret.append(urls)
        return ret

    def get_regions_v2(self):
        regions = []
        for service in self.catalog:
            if service['type'] != 'compute':
                continue
            endpoints = service['endpoints']
            for endpoint in endpoints:
                regions.append({'region': endpoint['region'],
                                'publicurl': endpoint['publicURL'],
                                'internalurl': endpoint['internalURL'],
                                })
        return regions

    def get_endpoint(self, region, service, ep_type, zone=None):
        if self.catalog is None:
            return None
        return self.get_endpoint_v3(region, service, ep_type, zone=zone)

    def get_endpoint_v3(self, region, service, ep_type, zone=None):
        if not ep_type.endswith('URL'):
            ep_type += 'URL'
        for s in self.catalog:
            if s['type'] == service:
                regions = {}
                for ep in s['endpoints']:
                    region = ep['region_id']
                    if region not in regions:
                        regions[region] = {}
                    regions[region]['%sURL' % ep['interface']] = ep['url']
                if region is None:
                    if len(regions) == 1:
                        for v in list(regions.values()):
                            return v[ep_type]
                    else:
                        raise Exception('No default region')
                else:
                    if zone is not None and len(zone) > 0:
                        region_zone = '%s-%s' % (region, zone)
                        if region_zone in regions:
                            return regions[region_zone][ep_type]
                    if region in regions:
                        return regions[region][ep_type]
                    raise Exception('No such region %s' % region)

    def get_endpoint_v2(self, region, service, ep_type, zone=None):
        for s in self.catalog:
            if s['type'] == service:
                sel_ep = None
                if region is None or len(region) == 0:
                    if len(s['endpoints']) == 1:
                        sel_ep = s['endpoints'][0]
                    else:
                        raise Exception('No default region')
                else:
                    reg_eps = []
                    region_zone = None
                    if zone is not None and len(zone) > 0:
                        zon_eps = []
                        region_zone = '%s-%s' % (region, zone)
                    for ep in s['endpoints']:
                        if ep['region'] == region:
                            reg_eps.append(ep)
                        elif region_zone is not None and \
                                ep['region'] == region_zone:
                            zon_eps.append(ep)
                    if region_zone is not None and len(zon_eps) > 0:
                        sel_ep = random.choice(zon_eps) # random for LB
                    elif len(reg_eps) > 0:
                        sel_ep = random.choice(reg_eps) # random for LB
                if sel_ep is not None and ep_type in sel_ep:
                    return sel_ep[ep_type]
        return None

    def from_json(self, desc):
        self.id = desc['id']
        self.name = desc['name']
        if 'token' in desc and 'catalog' in desc:
            user = desc.get('user', None)
            self.set_access_info(desc['token'], desc['catalog'], user,
                                                            no_check=True)

    def to_json(self):
        desc = {}
        desc['id'] = self.get_id()
        desc['name'] = self.get_name()
        if self.token and self.catalog:
            desc['token'] = self.token
            desc['catalog'] = self.catalog
            desc['user'] = self.user
        return desc

    def get_roles(self):
        if self.user is not None and 'roles' in self.user:
            return self.user['roles']
        else:
            return []

    def is_admin(self):
        for r in self.get_roles():
            if r['name'] == 'admin':
                return True
        return False

    def is_system_admin(self):
        if self.is_admin() and self.get_name() == 'system':
            return True
        else:
            return False

    def get_user_id(self):
        if self.user is not None and 'id' in self.user:
            return self.user['id']
        return None

    def get_user_name(self):
        if self.user is not None and 'name' in self.user:
            return self.user['name']
        return None

    def get_user_info(self):
        if self.user is not None:
            return self.user
        return None
