import MySQLdb
import os

from cmd import run_bash_cmd
from shutil import copyfile


class DB():
    def __init__(self, config=None, database="", host='127.0.0.1', user='root', passwd=None, port=3306):
        values = {
            'db_port': 3306,
            'db_host': '127.0.0.1',
        }
        if config:
            primary_master_config = getattr(config, 'primary_master_config', None)
            assert(primary_master_config)
            values.update(vars(primary_master_config))
            db = MySQLdb.connect(
                host=values['db_host'],
                user=values['db_user'],
                passwd=values['db_password'],
                db=database,
                charset='utf8',
                port=values['db_port'],
            )
        elif host:
            keys = ['host', 'user', 'passwd', 'db', 'charset', 'port']
            params = {'charset': 'utf8'}
            for key in keys:
                value = locals().get(key)
                if value:
                    params[key] = value
            db = MySQLdb.connect(**params)
        assert db
        self.database = database
        self.cursor = db.cursor()

    def fetchone(self, sql):
        self.cursor.execute(sql)
        return self.cursor.fetchone()[0]

    def fetchall(self, sql):
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get_databases(self):
        if self.database:
            return [self.database]
        ret = [i[0] for i in self.fetchall('show databases')]
        return sorted(list(set(ret) - set(['information_schema', 'mysql', 'performance_schema', 'test'])))

    def get_tables(self, exclude_prefix=''):
        ret = [i[0] for i in self.fetchall('show tables')]
        if not exclude_prefix:
            return ret
        else:
            return [i for i in ret if i.startswith(exclude_prefix)]

    def gen_export_args(self):
        ret = []
        for i in self.get_tables('opslog_tbl_'):
            ret.append('--ignore-table=%s.%s' % (self.database, i))
        return ' '.join(ret)

def gen_db_config_args(config):

    values = {
        'db_port': 3306,
        'db_host': '127.0.0.1',
    }

    primary_master_config = getattr(config, 'primary_master_config', None)
    assert(primary_master_config)
    values.update(vars(primary_master_config))
    return '-h "%(db_host)s" -u "%(db_user)s" -p"%(db_password)s" -P "%(db_port)s"' % values

def backup_db(config, backup_path):
    ignores = ''
    dbs = DB(config)
    for dbname in dbs.get_databases():
        db = DB(config, dbname)
        ignores += ' ' + db.gen_export_args()

    fn = '%s/onecloud.sql' % backup_path
    cmd = 'mysqldump --all-databases ' + gen_db_config_args(config) + ignores + ' --result-file ' + fn
    print('backing up to file: %s' % fn)
    run_bash_cmd(cmd)
    print('backup db OK. archiving... ')
    os.chdir(backup_path)
    run_bash_cmd('tar czvf onecloud.sql.tgz onecloud.sql')
    run_bash_cmd('rm -f onecloud.sql')
    print(run_bash_cmd('ls -lah %s/*tgz' % backup_path))


def backup_config(src, dest):
    output = os.path.join(dest, 'config.yml')
    print('backup config %s to %s... ' % (src, output))
    copyfile(src, output)
    print('backup config done')
