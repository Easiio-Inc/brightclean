#!/usr/bin/env python3
import sqlite3
from pathlib import Path
DB = Path('/home/jianl/class3-san-jose-cleaning-demo/data/class3-demo-crm.db')
if not DB.exists():
    raise SystemExit('Demo CRM database not found. Run ./start-demo.sh first.')
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
print('\n=== CLASS 3 DEMO CRM ===')
for table, fields in [
    ('contacts','id,name,email,phone,status,source'),
    ('deals','id,title,value,currency,stage,probability'),
    ('activities','id,kind,body,follow_up_at,completed')]:
    print(f'\n{table.upper()}')
    try:
        rows=con.execute(f'SELECT {fields} FROM {table} ORDER BY id DESC LIMIT 10').fetchall()
    except sqlite3.OperationalError as exc:
        print(f'  unavailable: {exc}'); continue
    if not rows: print('  (none yet)')
    for row in rows: print('  ' + ' | '.join(f'{k}={row[k]}' for k in row.keys()))
