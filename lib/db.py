import MySQLdb
import os

from cmd import run_bash_cmd, archive_with_pv
from shutil import copyfile
from .utils import print_title

PV_ARGS = 'pv --timer --eta'

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

    def get_db_size(self, dbs=[], tables=[], ignores=''):
        sql = 'SELECT ROUND(SUM(data_length)) AS "size_bytes" FROM information_schema.TABLES'
        if dbs:
            db_name_str = ', '.join(['"%s"' % i for i in dbs])
            sql += ' where TABLE_SCHEMA in (%s)' % db_name_str
            if tables:
                db_name_str = ','.join(['"%s"' % i for i in tables])
                sql += ' and TABLE_NAME in (%s)' % db_name_str
            if ignores:
                ignores = ignores.replace('--ignore-table=', '').replace('  ', ' ')
                ignores = ignores.split(' ')
                ignores = ', '.join(['"%s"' % i for i in ignores if i])
                ignores = ' and CONCAT(TABLE_SCHEMA, ".", TABLE_NAME) not in (%s)' % ignores
                sql += ignores
        return int(self.fetchone(sql))


def gen_db_config_args(config):

    values = {
        'db_port': 3306,
        'db_host': '127.0.0.1',
    }

    primary_master_config = getattr(config, 'primary_master_config', None)
    assert(primary_master_config)
    values.update(vars(primary_master_config))
    return ' -h "%(db_host)s" -u "%(db_user)s" -p"%(db_password)s" -P "%(db_port)s" ' % values


def backup_db_table(config, db, table):
    fn = '%s.%s.sql' % (db, table)
    tgz = '%s.%s.sql.tgz' % (db, table)
    _db = DB(config)
    db_size = _db.get_db_size([db], [table])
    db_args = gen_db_config_args(config)

    cmd = 'mysqldump --hex-blob --single-transaction --quick --databases %(db)s %(db_args)s --tables %(table)s ' % locals()  # + ' --result-file ' + fn
    cmd += ' | %(PV_ARGS)s --name " Dumping %(name)s" --size %(db_size)s' % {
        'PV_ARGS': PV_ARGS,
        'db_size': db_size,
        'name': db + '.' + table,
    }
    cmd += ' > %(fn)s' % locals()
    run_bash_cmd(cmd)
    archive_with_pv(fn, tgz)
    run_bash_cmd('rm -f %s' % fn)

def backup_db(config, backup_path):
    print_title('back up db...')
    os.chdir(backup_path)
    backup_db_table(config, 'yunionmeter', 'bills_tbl')
    backup_db_table(config, 'notify', 'tasks_tbl')
    ignores = ''
    dbs = DB(config)
    for dbname in dbs.get_databases():
        db = DB(config, dbname)
        ignores += ' ' + db.gen_export_args()
    db_name_str = ' '.join(dbs.get_databases())

    ignores += ' --ignore-table=yunionmeter.bills_tbl '
    ignores += ' --ignore-table=notify.tasks_tbl '

    fn = '%s/onecloud.sql' % backup_path
    cmd = 'mysqldump --hex-blob --single-transaction --quick --databases ' + db_name_str + ' ' + gen_db_config_args(config) + ignores

    db_size = dbs.get_db_size(dbs.get_databases(), ignores=ignores)
    cmd += ' | %(PV_ARGS)s --name " Dumping %(name)s" --size %(db_size)s' % {
        'PV_ARGS': PV_ARGS,
        'db_size': db_size,
        'name': fn,
    }
    cmd += ' > %s' % fn

    run_bash_cmd(cmd)
    archive_with_pv('onecloud.sql', 'onecloud.sql.tgz')
    run_bash_cmd('rm -f onecloud.sql')
    run_bash_cmd('ls -lah %s/*tgz' % backup_path)

def backup_config(src, dest):
    print_title('backing up the config')
    output = os.path.join(dest, 'config.yml')
    print('backup config %s to %s... ' % (src, output))
    copyfile(src, output)
