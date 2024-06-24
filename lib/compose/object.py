import yaml

from lib.compose import SERVICE_RESTART_ON_FAILURE


class Quoted(str):
    pass


def quoted_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    yaml.add_representer(quoted, quoted_presenter)


class Utils(object):

    @classmethod
    def dump_yaml(cls, data):
        yaml.add_representer(Quoted, quoted_presenter)

        output = yaml.dump(data, default_flow_style=False, sort_keys=False)
        return output


class ComposeObject(object):

    @classmethod
    def inject_data(cls, data_dict, name, data, list_as_dict=None):
        if not data:
            return
        if isinstance(data, list):
            if list_as_dict is None:
                list_as_dict = name in ["services", "networks", "volumes", "configs", "secrets"]
            for v in data:
                if data_dict.get(name, None) is None:
                    if list_as_dict:
                        data_dict[name] = {}
                    else:
                        data_dict[name] = []
                if isinstance(v, ComposeObject):
                    if list_as_dict:
                        data_dict[name][v.get_name()] = v.to_output()
                    else:
                        data_dict[name].append(v.to_output())
                else:
                    # print(f'{data_dict[name]} {name} append {v}')
                    data_dict[name].append(v)
        else:
            if hasattr(data, '__len__'):
                if len(data) == 0:
                    return
            data_dict[name] = data

    def to_output(self):
        raise Exception("to_output is not implemented")

    def to_yaml(self):
        return Utils.dump_yaml(self.to_output())


class DependOn(ComposeObject):
    # specifies that a service is started
    CONDITION_SERVICE_STARTED = "service_started"
    # specifies that a dependency is expected to be “healthy” (as indicated by healthcheck) before starting a dependent service.
    CONDITION_SERVICE_HEALTHY = "service_healthy"
    # specifies that a dependency is expected to run to successful completion before starting a dependent service.
    CONDITION_COMPLETED_SUCCESSFULLY = "service_completed_successfully"

    def __init__(self, service, condition, restart=False):
        self.service = service
        self.condition = condition
        self.restart = restart

    def get_name(self):
        return self.service.get_name()

    def to_output(self):
        out = {
            "condition": self.condition,
        }
        if self.restart:
            out["restart"] = self.restart
        return out


class Service(ComposeObject):

    def __init__(self, name, image):
        self.name = name
        self.image = image
        self.volumes = []
        self.ports = []
        self.environment = {}
        self.env_file = []
        self.depends_on = {}
        self.command = []
        self.healthcheck = None
        self.restart = None
        self.privileged = False
        self.network_mode = None

    def get_name(self):
        return self.name

    def add_volume(self, *vol):
        self.volumes = self.volumes + list(vol)
        return self

    def get_volumes(self):
        return self.volumes

    def add_port(self, *port):
        self.ports = self.ports + list(port)
        return self

    def enable_privileged(self):
        self.privileged = True

    def use_host_network(self):
        self.network_mode = "host"

    def is_host_network(self):
        return self.network_mode == "host"

    def add_environment(self, env):
        for key in env:
            self.environment[key] = env[key]
        return self

    def add_environment_file(self, env_file):
        self.env_file.append(env_file)
        return self

    def depend_on(self, service,
                  condition=DependOn.CONDITION_SERVICE_STARTED, restart=False):
        depend_on = DependOn(service, condition, restart)
        self.depends_on[depend_on.get_name()] = depend_on.to_output()
        return self

    def depend_on_health(self, service, restart=False):
        return self.depend_on(service,
                              condition=DependOn.CONDITION_SERVICE_HEALTHY,
                              restart=restart)

    def depend_on_completed(self, service, restart=False):
        return self.depend_on(service,
                              condition=DependOn.CONDITION_COMPLETED_SUCCESSFULLY,
                              restart=restart)

    def set_command(self, *command):
        self.command = list(command)
        return self

    def set_healthcheck(self, test,
                        interval=5,
                        timeout=10,
                        retries=10,
                        start_period=30):
        self.healthcheck = {
            'test': test,
            'interval': f'{interval}s',
            'timeout': f'{timeout}s',
            'retries': retries,
            'start_period': f'{start_period}s'
        }
        return self

    def set_restart(self, restart_policy):
        self.restart = restart_policy
        return self

    def set_restart_on_failure(self):
        return self.set_restart(SERVICE_RESTART_ON_FAILURE)

    def get_ports(self):
        return self.ports

    def to_output(self):
        data = {
            "image": self.image,
        }

        self.inject_data(data, "ports", self.get_ports(), list_as_dict=False)
        self.inject_data(data, "volumes", self.get_volumes(), list_as_dict=False)
        self.inject_data(data, "environment", self.environment)
        self.inject_data(data, "env_file", self.env_file)
        self.inject_data(data, "depends_on", self.depends_on)
        self.inject_data(data, "command", self.command)
        self.inject_data(data, "healthcheck", self.healthcheck)
        self.inject_data(data, "restart", self.restart)
        if self.privileged:
            self.inject_data(data, "privileged", self.privileged)
        if self.network_mode:
            self.inject_data(data, "network_mode", self.network_mode)

        return data


class ServiceVolume(ComposeObject):
    BIND_PROPAGATION_SHARED = "shared"

    def __init__(self, src, target, readonly=False, bind=None):
        self.src = src
        self.target = target
        self.readonly = readonly
        self.bind = bind

    def __str__(self):
        ret = '%s:%s' % (self.src, self.target)
        if self.readonly:
            ret = f"{ret}:ro"
        return ret

    def to_output(self):
        if self.bind:
            return {
                "type": "bind",
                "source": self.src,
                "target": self.target,
                "read_only": self.readonly,
                "bind": {
                    "propagation": self.bind,
                },
            }
        else:
            return self.__str__()


class ServiceDataVolume(ServiceVolume):
    SRC_DATA_DIR = "./data"

    def __init__(self, target_dir, readonly=False, bind=None):
        super().__init__(
            self.SRC_DATA_DIR + target_dir,
            target_dir,
            readonly=readonly, bind=bind)


class ServicePort(ComposeObject):

    def __init__(self, src, target, protocol='tcp'):
        self.src_port = src
        self.target_port = target
        self.protocol = protocol

    def __str__(self):
        return '%s:%s/%s' % (self.src_port, self.target_port, self.protocol)

    def to_output(self):
        return self.__str__()


class ComposeManifest(ComposeObject):

    def __init__(self, version="3.9"):
        self.version = version
        self.services = []
        self.volumes = []

    def add_service(self, *svc):
        if svc is None:
            return self
        self.services = self.services + list(svc)
        return self

    def add_volume(self, *vols):
        self.volumes = self.volumes + list(vols)
        return self

    def to_output(self):
        result = {}
        self.inject_data(result, "version", self.version)
        self.inject_data(result, "services", self.services)
        self.inject_data(result, "volumes", self.volumes)
        return result
