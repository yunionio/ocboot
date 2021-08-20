# encoding: utf-8
import subprocess
import os
import json


def get_ansible_config_path():
    return os.path.join(os.getcwd(), 'onecloud/ansible.cfg')


def _run_cmd(cmds):
    shell_cmd = ' '.join(cmds)
    print(shell_cmd)
    os.environ['ANSIBLE_FORCE_COLOR'] = '1'
    config_file = get_ansible_config_path()
    if not os.path.exists(config_file):
        raise Exception("Not found file %s" % config_file)
    os.environ['ANSIBLE_CONFIG'] = get_ansible_config_path()
    proc = subprocess.Popen(
        shell_cmd,
        shell=True,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,)
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        print(line.rstrip())
    proc.wait()
    return proc.returncode


def run_ansible_playbook(hosts_f, playbook_f, debug_level=0, vars=None):
    """
    debug level support example:
    VERBOSE_LEVEL=4 /opt/yunionboot/run.py /opt/yunion/upgrade/config.yml
    """
    debug_flag = ''
    if debug_level == 0:
        debug_level = int(os.environ.get('VERBOSE_LEVEL', 0))
    if debug_level > 0:
        if debug_level > 0:
            debug_flag = '-' + 'v' * debug_level

    cmd = ["ansible-playbook"]

    if vars:
        cmd.extend(["-e", "'%s'" % json.dumps(vars)])

    cmd.extend(["-i", hosts_f, playbook_f])

    if len(debug_flag) > 0:
        cmd.append(debug_flag)
    return _run_cmd(cmd)


def run_bash_cmd(cmd):
    import os
    os.system(cmd)


def ensure_pv():
    if not os.path.isfile('/usr/bin/pv'):
        run_bash_cmd('yum install -y pv >/dev/null')


def archive_with_pv(fn, output):
    cmd = '''tar cf - %(fn)s | pv --name ' Archiving %(fn)s' -s $(($(du -sk %(fn)s | awk '{print $1}') * 1024)) | gzip > %(output)s''' % locals()
    run_bash_cmd(cmd)


def extract_with_pv(archive):
    cmd = '''pv %(archive)s --name %(archive)s | tar -zx''' % locals()
    run_bash_cmd(cmd)