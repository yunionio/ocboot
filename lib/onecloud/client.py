import copy
import logging
import os
import json

import httplib2

from .tenantinfo import TenantInfo, TenantInfoManager
from . import exceptions


USER_AGENT = "ocboot-python-clien"
logger = logging.getLogger(__name__)


class HTTPClient(httplib2.Http):

    def __init__(self, timeout, insecure):
        super(HTTPClient, self).__init__(
            timeout=timeout,
            disable_ssl_certificate_validation=insecure)
        # httplib2 overrides
        self.force_exception_to_status_code = True

    def http_log(self, args, kwargs, resp, body):
        if os.environ.get('YUNIONCLIENT_DEBUG', True):
            ch = logging.StreamHandler()
            logger.setLevel(logging.DEBUG)
            logger.addHandler(ch)
        elif not logger.isEnabledFor(logging.DEBUG):
            return

        string_parts = ['curl -i']
        for element in args:
            if element in ('GET', 'POST'):
                string_parts.append(' -X %s' % element)
            else:
                string_parts.append(' %s' % element)

        for element in kwargs['headers']:
            header = ' -H "%s: %s"' % (element, kwargs['headers'][element])
            string_parts.append(header)

        logger.debug("REQ: %s\n" % "".join(string_parts))
        if 'raw_body' in kwargs:
            logger.debug("REQ BODY (RAW): %s\n" % (kwargs['raw_body']))
        if 'body' in kwargs:
            logger.debug("REQ BODY: %s\n" % (kwargs['body']))
        logger.debug("RESP: %s\nRESP BODY: %s\n", resp, body)

    def _strip_version(self, endpoint):
        """Strip a version from the last component of an endpoint if present"""

        # Get rid of trailing '/' if present
        while endpoint.endswith('/'):
            endpoint = endpoint[:-1]
        url_bits = endpoint.split('/')
        # regex to match 'v1' or 'v2.0' etc
        import re
        if re.match('v\d+\.?\d*', url_bits[-1]):
            endpoint = '/'.join(url_bits[:-1])
        return endpoint

    def _get_urllib2_raw_request(self, endpoint, auth_token, method, url,
                                    **kwargs):
        import urllib.request, urllib.error, urllib.parse
        url = endpoint + url
        url = url.encode('UTF-8')
        req = urllib.request.Request(url)
        headers = copy.deepcopy(kwargs.get('headers', {}))
        headers.setdefault('User-Agent', USER_AGENT)
        headers.setdefault('Connection', 'Close')
        if auth_token:
            headers.setdefault('X-Auth-Token', auth_token)
        for h in list(headers.keys()):
            req.add_header(h, headers[h])
        if 'body' in kwargs:
            req.add_data(kwargs['body'])
        return urllib.request.urlopen(req)

    def _http_request(self, endpoint, auth_token, url, method, **kwargs):
        """ Send an http request with the specified characteristics.
        Wrapper around httplib2.Http.request to handle tasks such as
        setting headers, JSON encoding/decoding, and error handling.
        """
        url = endpoint + url

        # Copy the kwargs so we can reuse the original in case of redirects
        kwargs['headers'] = copy.deepcopy(kwargs.get('headers', {}))
        kwargs['headers'].setdefault('User-Agent', USER_AGENT)
        #kwargs['headers'].setdefault('Accept-Encoding', 'identity')
        if auth_token:
            kwargs['headers'].setdefault('X-Auth-Token', auth_token)

        if 'body' not in kwargs and method in ['POST', 'PUT']:
            kwargs['headers'].setdefault('Content-length', '0')

        #print url
        #print kwargs['headers']
        resp, body = super(HTTPClient, self).request(url, method, **kwargs)
        self.http_log((url, method,), kwargs, resp, body)

        #print resp
        #print 'BODY', body

        if 400 <= resp.status < 600:
            #logger.exception("Request returned failure status.")
            raise exceptions.from_response(resp, body)
        elif resp.status in (301, 302, 305):
            # Redirected. Reissue the request to the new location.
            return self._http_request(resp['location'], method, **kwargs)

        return resp, body

    def _json_request(self, endpoint, auth_token, method, url, **kwargs):
        kwargs.setdefault('headers', {})

        if 'body' in kwargs and kwargs['body'] is not None:
            kwargs['headers'].setdefault('Content-Type', 'application/json')
            kwargs['body'] = json.dumps(kwargs['body'])

        resp, body = self._http_request(endpoint, auth_token, url, method,
                                        **kwargs)

        if body:
            try:
                body = json.loads(body)
            except ValueError:
                logger.debug("Could not decode JSON from body: %s" % body)
        else:
            logger.debug("No body was returned.")
            body = None

        return resp, body

    def _raw_request(self, endpoint, auth_token, method, url, **kwargs):
        kwargs.setdefault('headers', {})

        if 'body' in kwargs and kwargs['body'] is not None:
            kwargs['headers'].setdefault('Content-Type',
                                     'application/octet-stream')
        return self._http_request(endpoint, auth_token, url, method, **kwargs)


class Client(HTTPClient):

    def __init__(self, auth_url, username, password, domain_name,
                 region=None, zone=None, endpoint_type='publicURL',
                 timeout=600, insecure=False):
        super(Client, self).__init__(timeout, insecure)

        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.domain_name = domain_name
        self.endpoint_type = endpoint_type
        self.set_region(region, zone)

        self.default_tenant = None
        self.tenants_info_manager = TenantInfoManager()

    def set_region(self, region, zone=None):
        self.region = region
        self.zone = zone

    def _authenticatev3(self, project_name=None, project_id=None):
        logging.info('authenticate %s %s' % (project_name, project_id))
        auth = {}
        user = {'name': self.username, 'password': self.password}
        if self.domain_name:
            user['domain'] = {'name': self.domain_name}
        else:
            user['domain'] = {'id': 'default'}
        auth['identity'] = {'methods': ['password'],
                            'password': {'user': user}}
        project = {}
        if project_name:
            project['name'] = project_name
            project['domain'] = {'id': 'default'}
        if project_id:
            project['id'] = project_id
        auth['scope'] = {'project': project}
        body = {'auth': auth}
        resp, body = self._json_request(self.auth_url, None,
                                            'POST', '/auth/tokens', body=body)
        if 'token' in body:
            token_id = resp['x-subject-token']
            if 'project' in body['token']:
                self.default_tenant = TenantInfo(None, None)
                token = {'id': token_id,
                        'tenant': body['token']['project'],
                        'expires': body['token']['expires_at']}
                catalog = body['token']['catalog']
                user = body['token']['user']
                self.default_tenant.set_access_info(token, catalog, user)
                self.tenants_info_manager.add_tenant(self.default_tenant)
            else:
                self._fetch_tenants(token_id)
            return True
        else:
            raise Exception('Wrong return format %s' % json.dumps(body))

    def _authenticate(self, tenant_name=None, tenant_id=None):
        logging.info('authenticate %s %s' % (tenant_name, tenant_id))
        auth = {}
        auth['passwordCredentials'] = {'username': self.username,
                                        'password': self.password}
        if tenant_id is not None and len(tenant_id) > 0:
            auth['tenantId'] = tenant_id
        elif tenant_name is not None and len(tenant_name) > 0:
            auth['tenantName'] = tenant_name
        body = {'auth': auth}
        resp, body = self._json_request(self.auth_url, None,
                                            'POST', '/tokens', body=body)
        # print json.dumps(body, indent=4)
        if 'access' in body:
            token = body['access']['token']
            catalog = body['access']['serviceCatalog']
            user = body['access']['user']
            if 'tenant' in token:
                self.default_tenant = TenantInfo(None, None)
                # print 'Token:', token
                self.default_tenant.set_access_info(token, catalog, user)
                self.tenants_info_manager.add_tenant(self.default_tenant)
            else:
                self._fetch_tenants(token['id'])
            return True
        else:
            raise Exception('Wrong return format %s' % json.dumps(body))
        return False

    def _fetch_tenants(self, token):
        try:
            resp, body = self._json_request(self.auth_url, token,
                                            'GET', '/tenants')
            if 'tenants' in body:
                for t in body['tenants']:
                    self.tenants_info_manager.add_tenant(TenantInfo(t['id'],
                                                                    t['name']))
            return True
        except Exception as e:
            raise Exception('_fetch_tenants %s' % e)
        return False

    def get_tenants(self):
        self._authenticate(None, None)
        return self.tenants_info_manager.get_tenants()

    def set_project(self, project_name=None, project_id=None):
        return self.set_tenant(tenant_name=project_name, tenant_id=project_id)

    def set_tenant(self, tenant_name=None, tenant_id=None):
        tenant = self.tenants_info_manager.get_tenant(tenant_id=tenant_id,
                                                        tenant_name=tenant_name)
        if tenant is None:
            return self._authenticatev3(project_name=tenant_name,
                                            project_id=tenant_id)
        else:
            self.default_tenant = tenant
            return True

    def get_default_tenant(self):
        if self.default_tenant is None:
            raise Exception('No tenant specified')
        # if self.default_tenant.expire_soon():
        #    self._authenticate(tenant_name=self.default_tenant.get_name(),
        #                        tenant_id=self.default_tenant.get_id())
        return self.default_tenant

    def get_regions(self):
        t = self.get_default_tenant()
        if t is not None:
            return t.get_regions()
        else:
            return None

    def get_endpoint(self, service, admin_api=False, region=None, zone=None):
        t = self.get_default_tenant()
        if t is not None:
            if admin_api:
                ep_type = 'adminURL'
            else:
                ep_type = self.endpoint_type
            if region is None:
                region = self.region
            if zone is None:
                zone = self.zone
            return t.get_endpoint(region, service, ep_type, zone=zone)
        else:
            raise Exception('No tenant specified')

    def _wrapped_request(self, func, service, admin_api, method, url, **kwargs):
        t = self.get_default_tenant()
        if t is not None:
            ep = self.get_endpoint(service, admin_api)
            if ep is not None:
                ep = self._strip_version(ep)
                return func(ep, t.get_token(), method, url, **kwargs)
            else:
                raise Exception('NO valid endpoint found for %s' % service)
        else:
            raise Exception('No tenant specified')

    def json_request(self, service, admin_api, method, url, **kwargs):
        return self._wrapped_request(self._json_request, service, admin_api,
                                                        method, url, **kwargs)

    def raw_request(self, service, admin_api, method, url, **kwargs):
        return self._wrapped_request(self._raw_request, service, admin_api,
                                                        method, url, **kwargs)

    def get_urllib2_raw_request(self, service, admin_api, url, **kwargs):
        return self._wrapped_request(self._get_urllib2_raw_request, service,
                                                admin_api, 'GET', url, **kwargs)

    def from_file(self, filename):
        with open(filename, 'r') as f:
            desc = f.read()
            self.from_json(json.loads(desc))

    def from_json(self, desc):
        self.auth_url = desc['auth_url']
        self.username = desc['username']
        self.endpoint_type = desc['endpoint_type']
        self.set_region(desc['region'], desc.get('zone', None))
        self.tenants_info_manager = TenantInfoManager()
        self.tenants_info_manager.from_json(desc['tenants'])
        if 'default_tenant_id' in desc:
            self.set_tenant(tenant_id=desc['default_tenant_id'])

    def to_file(self, filename):
        with open(filename, 'w') as f:
            desc = self.to_json()
            f.write(json.dumps(desc))

    def to_json(self):
        desc = {}
        desc['tenants'] = self.tenants_info_manager.to_json()
        desc['username'] = self.username
        desc['auth_url'] = self.auth_url
        desc['region'] = self.region
        if self.zone:
            desc['zone'] = self.zone
        desc['endpoint_type'] = self.endpoint_type
        if self.default_tenant is not None:
            desc['default_tenant_id'] = self.default_tenant.get_id()
        return desc

    def is_admin(self):
        tenant = self.get_default_tenant()
        if tenant is not None:
            return tenant.is_admin()
        return False

    def is_system_admin(self):
        tenant = self.get_default_tenant()
        if tenant is not None:
            return tenant.is_system_admin()
        return False


if __name__ == '__main__':
    desc = {
        'project_name': 'system',
        'project_id': None,
        'args': (
            'https://10.1.2.56:30500/v3',
            'sysadmin',
            'HXf7J7zAw59FpAJz',
            None,
        ),
        'kwargs': {
            'region': 'region0',
            'zone': None,
            'insecure': True,
            'endpoint_type': 'publicURL',
        }
    }

    args = desc['args']
    kwargs = desc['kwargs']

    client = Client(*args, *kwargs)
    client.set_project(desc.get('project_name'))
    import ipdb; ipdb.set_trace()
