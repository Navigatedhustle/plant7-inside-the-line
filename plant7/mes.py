"""Read-only SELECT sandbox. Table and function allowlists prevent file/network IO."""
import datetime
import threading
from decimal import Decimal

import duckdb
import sqlglot
from sqlglot import exp

from .settings import DB, TABLES

SAFE_FUNCTIONS = {'COUNT', 'AVG', 'SUM', 'MIN', 'MAX', 'ROUND', 'ABS', 'COALESCE', 'NULLIF',
                  'CAST', 'TRY_CAST', 'DATE_TRUNC', 'EXTRACT', 'STDDEV_POP', 'STDDEV_SAMP',
                  'PERCENTILE_CONT', 'MEDIAN', 'LOWER', 'UPPER', 'DATE', 'STRFTIME', 'DATEDIFF',
                  'AND', 'OR', 'NOT', 'IN', 'BETWEEN', 'IF', 'CASE', 'TS_OR_DS_TO_DATE'}


def validate_sql(sql):
    if not sql.lstrip().upper().startswith('SELECT'):
        raise ValueError('Only a single SELECT is accepted')
    statements = sqlglot.parse(sql, read='duckdb')
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError('Only a single SELECT is accepted')
    tree = statements[0]
    if tree.find(exp.Into) or tree.find(exp.Command):
        raise ValueError('SELECT output targets and commands are forbidden')
    for table in tree.find_all(exp.Table):
        if table.name not in TABLES or table.db or table.catalog or not isinstance(table.this, exp.Identifier):
            raise ValueError('Only named MES tables are accessible')
    for func in tree.find_all(exp.Func):
        name = func.name.upper() if isinstance(func, exp.Anonymous) else func.sql_name().upper()
        if name not in SAFE_FUNCTIONS and not isinstance(func, (exp.Case, exp.If)):
            raise ValueError('Function not allowed: ' + name)
    return tree.sql(dialect='duckdb')


def schema():
    with duckdb.connect(str(DB), read_only=True, config={'enable_external_access': False,
                         'threads': 2, 'memory_limit': '1GB'}) as db:
        return '\n'.join(name + ': ' + ', '.join(str(row[0]) + ' ' + str(row[1])
                         for row in db.execute('DESCRIBE ' + name).fetchall()) for name in TABLES)


def query_mes(sql, database=None):
    safe = validate_sql(sql)
    # Alternate fixture paths are code selected, never accepted as user input.
    chosen = DB if database is None else database.resolve()
    allowed = {DB.resolve()} | {(DB.parent / 'scenarios' / (name + '.duckdb')).resolve() for name in
        ('no_anomaly','different_tool','missing_video','inconclusive_sequence','supplier_issue')}
    if chosen.resolve() not in allowed:
        raise ValueError('Database is outside the project fixture allowlist')
    db = duckdb.connect(str(chosen), read_only=True, config={'enable_external_access': False,
                        'threads': 2, 'memory_limit': '1GB'})
    timeout = threading.Timer(5, db.interrupt)
    timeout.start()
    try:
        result = db.execute(safe)
        columns = [item[0] for item in result.description]
        raw = result.fetchmany(1001)
        def value(v):
            if isinstance(v, (datetime.date, datetime.datetime)):
                return v.isoformat()
            if isinstance(v, Decimal):
                return float(v)
            return v
        return {'sql': safe, 'columns': columns, 'rows': [dict(zip(columns, map(value, row))) for row in raw[:1000]],
                'truncated': len(raw) > 1000}
    finally:
        timeout.cancel()
        timeout.join()
        db.close()
