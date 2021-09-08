# encoding: utf-8
import logging

import paramiko

from . import logger


logger = logger.new(__name__)


class StderrException(Exception):
    pass


class SSHClient(object):

    def __init__(self, host, user, private_key_f, port=22):
        self.host = host
        self.port = port
        self.user = user
        self.private_key_file = private_key_f
        self.client = self.new_ssh_client()

    def new_ssh_client(self):
        k = paramiko.RSAKey.from_private_key_file(self.private_key_file)
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(
            hostname=self.host,
            port=self.port,
            username=self.user,
            pkey=k)
        return c

    def exec_command(self, command):
        command = '%s %s' % ('[ -s /etc/kubernetes/admin.conf ] && export KUBECONFIG=/etc/kubernetes/admin.conf || :;', command)
        logger.info("exec_command: %s" % command)
        _, stdout, stderr = self.client.exec_command(command)
        out = stdout.read()
        err = stderr.read()
        if err:
            raise StderrException(err)
        return out
