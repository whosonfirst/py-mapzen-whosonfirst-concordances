# https://pythonhosted.org/setuptools/setuptools.html#namespace-packages
# __import__('pkg_resources').declare_namespace(__name__)

import sys
import logging

def cfg2dsn(cfg, sect):
    db_user = cfg.get(sect, 'db_user')
    db_pswd = cfg.get(sect, 'db_pswd')
    db_host = cfg.get(sect, 'db_host')
    db_name = cfg.get(sect, 'db_name')
    
    dsn = "dbname=%s user=%s password=%s host=%s" % (db_name, db_user, db_pswd, db_host)
    return dsn

class db:

    def __init__(self, dsn, **kwargs):

        engine = kwargs.get('engine', 'sqlite3')

        if engine == 'psycopg2':            

            import pyscopg2                
            conn = psycopg2.connect(dsn)
            curs = conn.cursor()
            placeholder = "%" + "s"

        elif engine != "sqlite3":
            raise Exception, "Unsupported database engine"

        else:

            import sqlite3
            conn = sqlite3.connect(dsn)
            curs = conn.cursor()
            placeholder = "?"

        self.conn = conn
        self.curs = curs
        self.placeholder = placeholder


class index(db):

    def import_concordances(self, wof_id, concordances, **kwargs):

        if kwargs.get('purge', False):
            self.purge_concordances(wof_id)

        for other_src, other_id in concordances.items():
            self.import_concordance(wof_id, other_id, other_src)

    def import_concordance(self, wof_id, other_id, other_src=''):

        sql = "INSERT INTO concordances (wof_id, other_id, other_src) VALUES (%s, %s, %s)" % (self.placeholder, self.placeholder, self.placeholder)
        params = (wof_id, other_id, other_src)

        logging.debug("import %s" % str(params))

        try:
            self.curs.execute(sql, params)
            self.conn.commit()

            # Please trap me and check type(e) I guess...
            # (20151208/thisisaaronland)
            #
            #        except psycopg2.IntegrityError, e:
            #            logging.debug("%s is already concordified with %s %s" % (wof_id, other_src, other_id))
            #            self.conn.rollback()
            
        except Exception, e:
            logging.error("failed to concordify %s because %s" % (wof_id, e))
            self.conn.rollback()
            raise Exception, e

    def purge_concordances(self, wof_id):

        sql = "DELETE FROM concordances WHERE wof_id=%s" % self.placeholder
        params = (wof_id,)

        logging.debug(sql % params)

        try:
            self.curs.execute(sql, params)
            self.conn.commit()
        except Exception, e:
            logging.error("failed to purge concordances for %s, because %s" % (wof_id, e))
            self.conn.rollback()
            raise Exception, e
            

class query(db):

    def others(self):

        sql = "SELECT DISTINCT(other_src) FROM concordances"
        self.curs.execute(sql)

        for row in self.curs.fetchall():
            yield row[0]
        
    def dump(self):

        sql = "SELECT * FROM concordances"
        self.curs.execute(sql)

        for row in self.curs.fetchall():
            yield row
        
    def wof_ids(self, exclude=[]):

        sql = "SELECT DISTINCT(wof_id) AS wof_id FROM concordances"
        params = []

        if len(exclude):

            placeholders = []

            for e in exclude:
                params.append(e)
                placeholders.append(self.placeholder)

            placeholders = ",".join(placeholders)

            sql += " WHERE other_src NOT IN (" + placeholders + ")"

        self.curs.execute(sql, params)

        for row in self.curs.fetchall():
            yield row

    def by_wof_id(self, wof_id):

        sql = "SELECT * FROM concordances WHERE wof_id=%s" % self.placeholder
        params = (wof_id,)

        self.curs.execute(sql, params)

        for row in self.curs.fetchall():
            yield row

    def by_wof_id_for_other(self, wof_id, other_src):

        sql = "SELECT * FROM concordances WHERE wof_id=%s AND other_src=%s" % self.placeholder
        params = (wof_id, other_src)

        self.curs.execute(sql, params)
        return self.curs.fetchone()

    def by_other_id(self, other_id, other_src):

        sql = "SELECT * FROM concordances WHERE other_src=%s AND other_id=%s" % (self.placeholder, self.placeholder)
        params = map(str, (other_src, other_id))

        self.curs.execute(sql, params)
        return self.curs.fetchone()
