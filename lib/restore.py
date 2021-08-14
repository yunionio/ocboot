# encoding: utf-8

import os
import yaml
from . import ocboot
from .db import DB
from .db import gen_db_config_args
from .cmd import run_bash_cmd
from .utils import animated_waiting, to_yaml

ROOT_PATH = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

def add_command(subparsers):
    parser = subparsers.add_parser(
        "restore", help="restore onecloud cluster")
    parser.add_argument('--backup-path', dest='backup_path', help="backup path. default: /opt/backup", default="/opt/backup")
    parser.add_argument('--install-db-to-localhost', action='store_true', help="use this option when install local db")
    parser.add_argument('primary_ip', help="primary node ip")
    parser.add_argument('--master-node-ips', help="master nodes ips, seperated by comma ','")
    parser.add_argument('--master-node-as-host', action='store_true', help="use this option when use master nodes as host")
    parser.add_argument('--worker-node-ips', help="worker nodes ips, seperated by comma ','")
    parser.add_argument('--worker-node-as-host', action='store_true', help="use this option when use worker nodes as host")
    parser.add_argument('--mysql-host', help="mysql host; not needed if set --install-db-to-localhost")
    parser.add_argument('--mysql-user', default='root', help="mysql user, default: root; not needed if set --install-db-to-localhost")
    parser.add_argument('--mysql-password', help="mysql password; not needed if set --install-db-to-localhost")
    parser.add_argument('--mysql-port', default=3306, help="mysql port, default: 3306; not needed if set --install-db-to-localhost", type=int)
    parser.set_defaults(func=do_restore)

def get_backup_db_password(args):
    config_file = os.path.join(args.backup_path, 'config.yml')
    assert os.path.exists(config_file), "the config file " + config_file + " dose not exist!"
    config = ocboot.load_config(config_file)
    primary_master_config = getattr(config, 'primary_master_config', None)
    db_password = getattr(primary_master_config, 'db_password', None)
    assert db_password, "the backup database password must not be empty!"
    return db_password

db_config = {}

def ensure_db_config(args):
    global db_config
    if db_config:
        return db_config
    ret = {}
    ip = args.primary_ip
    if args.install_db_to_localhost:
        ret['host'] = ip
    elif args.mysql_host:
        ret['host'] = args.mysql_host
    else:
        raise Exception("please set --install-db-to-localhost or --mysql-host option.")

    ret['port'] = args.mysql_port or '3306'
    ret['user'] = args.mysql_user or 'root'
    ret['passwd'] = args.mysql_password
    if not args.mysql_password:
        ret['passwd'] = get_backup_db_password(args)

    if args.install_db_to_localhost:
        # install
        print(run_bash_cmd('systemctl is-active mariadb > /dev/null || yum install -y mariadb-server && systemctl enable --now mariadb'))
        # set password
        sql = ''' grant all privileges on *.* to `%(user)s`@`%%` identified by "%(passwd)s" with grant option;FLUSH PRIVILEGES;''' % ret
        db = DB()
        db.cursor.execute(sql)
    db_config.update(ret)
    return db_config


def restore_db(args):
    # config_file = os.path.join(args.backup_path, 'config.yml')
    db_file_tar = os.path.join(args.backup_path, 'onecloud.sql.tgz')
    db_file_sql = os.path.join(args.backup_path, 'onecloud.sql')
    assert os.path.exists(db_file_tar), "the config file " + db_file_tar + " dose not exist!"

    print('extracting db archive: ' + db_file_tar)
    os.chdir(args.backup_path)
    animated_waiting(run_bash_cmd, 'tar xzvf ' + db_file_tar)
    print(run_bash_cmd('ls -lah ' + args.backup_path))
    assert os.path.getsize('onecloud.sql') > 0, "the extracting db backup file onecloud.sql is empty!"

    db_args = '-h "%(host)s" -u "%(user)s" -p"%(passwd)s" -P "%(port)s"' % ensure_db_config(args)
    cmd = 'mysql ' + db_args + ' < ' + db_file_sql
    print('\nrestoring db from ' + db_file_sql)
    animated_waiting(run_bash_cmd, cmd)
    print('restore db OK')


def generate_nodes(args, role):
    '''
master_nodes:
  hosts:
  - hostname: $host1
    user: root
    use_local: false
  controlplane_host: $pri
  controlplane_port: "6443"
  as_controller: true
  registry_mirrors:
  - https://lje6zxpk.mirror.aliyuncs.com
    '''
    assert role in ['master', 'worker']
    ips = getattr(args, '%s_node_ips' % role)
    if not ips:
        return {}
    as_host = getattr(args, '%s_node_as_host' % role)
    vars = {
        'controlplane_host': args.primary_ip,
        'controlplane_port': "6443",
        'as_controller': True,
        'as_host': as_host,
        'registry_mirrors': ['https://lje6zxpk.mirror.aliyuncs.com'],
    }

    nodes = []
    for i in ips.split(','):
        node = {
            'hostname': i,
            'user': 'root',
        }
        nodes += [node]
    vars['hosts'] = nodes
    return vars


def restore_config(args):
    config_file = os.path.join(args.backup_path, 'config.yml')
    config_json = None
    with open(config_file, 'r') as stream:
        try:
            config_json = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # databases
    db_config = ensure_db_config(args)
    config_json['primary_master_node'].update({
        'db_host': db_config.get('host'),
        'db_password': db_config.get('passwd'),
        'db_port': db_config.get('port'),
        'db_user': db_config.get('user'),
    })

    config_json['mariadb_node'] = {
        "db_password": db_config.get('passwd'),
        "db_user": db_config.get('user'),
        "hostname": db_config.get('host'),
        "user": 'root',
    }

    # primary node ip update
    if config_json['primary_master_node'].get('controlplane_host') != config_json['primary_master_node'].get('node_ip'):
        raise Exception("Primary controlplane_host and node_ip are different. Not supported backup mode!")

    config_json['primary_master_node'].update({
        'controlplane_host': args.primary_ip,
        'node_ip': args.primary_ip,
        'ip_autodetection_method': 'can-reach=%s' % args.primary_ip,
        'restore_mode': True    # very important for restoring.
    })

    for i in ['keepalived_version_tag', 'host_networks', 'image_repository', 'insecure_registries']:
        if i in config_json['primary_master_node']:
            del config_json['primary_master_node'][i]

    for i in ['master_node_ips', 'worker_nodes']:
        if i in config_json:
            del config_json[i]

    if args.master_node_ips:
        config_json['master_nodes'] = generate_nodes(args, 'master')

    if args.worker_node_ips:
        config_json['worker_nodes'] = generate_nodes(args, 'worker')

    yaml_content = ''
    for i in ['mariadb_node', 'primary_master_node', 'master_nodes', 'worker_nodes']:
        if i in config_json:
            yaml_content += to_yaml({i: config_json[i]})

    config_output = os.path.join(ROOT_PATH, 'config.yml')
    os.chdir(ROOT_PATH)
    with open('config.yml', 'w') as f:
        try:
            f.write(yaml_content)
        except IOError as e:
            print('write yaml config to %s error: %s!' % (config_file, e))

    print("All done! please restore the k8s system by running:")
    print("%s/run.py %s/config.yml" % (ROOT_PATH, ROOT_PATH))

def do_restore(args):
    restore_db(args)
    restore_config(args)
