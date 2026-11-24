#!/usr/bin/env python3
"""Loopback-only BrightClean administration. Python standard library only."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import getpass
import hashlib
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit, parse_qs
from urllib.request import Request, urlopen

from backend.crm_core import SoloCRM

ROOT = Path(__file__).resolve().parent
SITE = 'class3-brightclean-san-jose'
ITERATIONS = 600_000
TTL = 3600
FIELDS = {
    'contacts': {'name':'','email':'','phone':'','role':'','status':'lead','source':'admin','notes':''},
    'deals': {'title':'','contact_id':None,'value':0,'currency':'USD','stage':'new','probability':0,'close_date':'','notes':''},
    'activities': {'contact_id':None,'deal_id':None,'kind':'note','body':'','follow_up_at':'','completed':0},
}

MODELS=('gpt-4o-mini','gpt-4o','gpt-4.1-mini','gpt-4.1')
LEAD_FIELDS={'name':('Name','text','name'),'email':('Email','email','email'),'phone':('Phone','text','tel'),'company':('Company','text','organization'),'message':('Message','textarea','')}

def default_settings():
    return {'site_id':SITE,'appearance':{'enabled':True,'title':'BrightClean Assistant','greeting':"Hi! Ask me about BrightClean's demo services, prices, service area, or policies.",'primary_color':'#123d3a','position':'bottom-right','launcher_style':'bubble','launcher_size':'small','avatar_url':''},'behavior':{'auto_open':False,'auto_open_delay_seconds':0,'track_page_views':True,'exclude_paths':[]},'business':{'organization_name':'BrightClean San Jose','website_name':'BrightClean San Jose','phone':'(408) 555-0147','email':'','service_area':'San Jose, California','hours':'Daily 8:00 AM–8:00 PM','website_url':'http://127.0.0.1:8188/','privacy_url':'','consent_text':'By chatting, you agree that we may use your message to follow up about BrightClean services.'},'lead_form':{'enabled':True,'title':'Where should we follow up?','description':'Optional — close this and keep chatting if you are not ready.','submit_label':'Send inquiry','fields':[{'name':'name','required':False},{'name':'email','required':True},{'name':'phone','required':False},{'name':'message','required':True}]}}

def default_llm_settings(): return {'provider':'OpenAI','model':'gpt-4o-mini','base_url':'https://api.openai.com/v1','restart_required':False}

def atomic_json(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); temporary=path.with_name(path.name+'.tmp')
    with open(temporary,'w',encoding='utf-8') as out:
        json.dump(data,out,indent=2,ensure_ascii=False); out.write('\n'); out.flush(); os.fsync(out.fileno())
    os.replace(temporary,path)

def read_json(path,default):
    try:
        value=json.loads(Path(path).read_text(encoding='utf-8')); return value if isinstance(value,dict) else default
    except (OSError,ValueError): return default

def save_api_key(root,key):
    target=Path(root)/'data/secrets/openai.env'; target.parent.mkdir(parents=True,exist_ok=True,mode=0o700); os.chmod(target.parent,0o700)
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as out: out.write('EASIIO_CHATBOT_LLM_API_KEY='+key+'\n')
    os.chmod(target,0o600)

def read_api_key(root):
    try:
        line=(Path(root)/'data/secrets/openai.env').read_text().strip(); return line.split('=',1)[1] if line.startswith('EASIIO_CHATBOT_LLM_API_KEY=') else ''
    except OSError: return ''

def valid_url(value,allow_http=True):
    if value=='': return True
    parsed=urlsplit(value); return parsed.scheme in (('http','https') if allow_http else ('https',)) and bool(parsed.netloc) and not parsed.username and not parsed.password

def validate_settings(value):
    require(isinstance(value,dict)); defaults=default_settings(); result={'site_id':SITE}
    require(not set(value)-set(defaults),message='Unknown settings section')
    for section in ('appearance','behavior','business','lead_form'):
        incoming=value.get(section); require(isinstance(incoming,dict),message=f'{section} is required'); require(not set(incoming)-set(defaults[section]),message=f'Unknown {section} setting')
        result[section]=dict(defaults[section]); result[section].update(incoming)
    ap,be,bi,lead=result['appearance'],result['behavior'],result['business'],result['lead_form']
    require(type(ap['enabled']) is bool and type(be['auto_open']) is bool and type(be['track_page_views']) is bool,message='Boolean setting required')
    require(isinstance(ap['title'],str) and len(ap['title'])<=120 and isinstance(ap['greeting'],str) and len(ap['greeting'])<=500)
    require(bool(re.fullmatch(r'#[0-9a-fA-F]{6}',ap['primary_color'])),message='Use a six-digit hex color')
    require(ap['position'] in ('bottom-right','bottom-left') and ap['launcher_style'] in ('bubble','capsule') and ap['launcher_size'] in ('small','medium','large'),message='Invalid appearance option')
    require(isinstance(ap['avatar_url'],str) and len(ap['avatar_url'])<=1000 and valid_url(ap['avatar_url']),message='Avatar URL must use http or https')
    require(type(be['auto_open_delay_seconds']) is int and 0<=be['auto_open_delay_seconds']<=60,message='Delay must be from 0 to 60 seconds')
    require(isinstance(be['exclude_paths'],list) and len(be['exclude_paths'])<=50 and all(isinstance(x,str) and x.startswith('/') and len(x)<=200 and '\\' not in x for x in be['exclude_paths']),message='Excluded paths must begin with /')
    for key in ('organization_name','website_name','phone','service_area','hours','consent_text'): require(isinstance(bi[key],str) and len(bi[key])<=500,message=f'Invalid {key}')
    require(isinstance(bi['email'],str) and len(bi['email'])<=254 and (not bi['email'] or bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',bi['email']))),message='Enter a valid email')
    for key in ('website_url','privacy_url'): require(isinstance(bi[key],str) and len(bi[key])<=1000 and valid_url(bi[key]),message=f'{key} must use http or https')
    require(type(lead['enabled']) is bool)
    for key,limit in [('title',120),('description',500),('submit_label',80)]: require(isinstance(lead[key],str) and len(lead[key])<=limit)
    require(isinstance(lead['fields'],list) and 1<=len(lead['fields'])<=len(LEAD_FIELDS)); names=[]
    for field in lead['fields']:
        require(isinstance(field,dict) and set(field)=={'name','required'} and field['name'] in LEAD_FIELDS and type(field['required']) is bool,message='Invalid lead field')
        require(field['name'] not in names,message='Duplicate lead field'); names.append(field['name'])
    return result

def validate_llm(value):
    require(isinstance(value,dict) and not set(value)-{'model','base_url','api_key','clear_key'},message='Unknown AI setting')
    model=value.get('model',''); base=value.get('base_url',''); key=value.get('api_key','')
    require(isinstance(model,str) and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,99}',model)),message='Invalid model name')
    require(isinstance(base,str) and len(base)<=500 and valid_url(base,False),message='Base URL must use HTTPS')
    require(isinstance(key,str) and (not key or (16<=len(key)<=500 and not any(c.isspace() for c in key))),message='Invalid API key')
    require(type(value.get('clear_key',False)) is bool)
    return {'provider':'OpenAI','model':model,'base_url':base,'restart_required':True}

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest}'

def valid_hash(encoded):
    try:
        kind, rounds, salt, digest = encoded.split('$')
        return kind == 'pbkdf2_sha256' and 600_000 <= int(rounds) <= 2_000_000 and len(bytes.fromhex(salt)) == 16 and len(bytes.fromhex(digest)) == 32
    except (ValueError, TypeError):
        return False

def verify_password(password, encoded):
    if not valid_hash(encoded): return False
    _, rounds, salt, expected = encoded.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds)).hex()
    return hmac.compare_digest(actual, expected)

def credentials():
    username = os.environ.get('BRIGHTCLEAN_ADMIN_USERNAME', 'admin')
    encoded = os.environ.get('BRIGHTCLEAN_ADMIN_PASSWORD_HASH')
    password = os.environ.get('BRIGHTCLEAN_ADMIN_DEV_PASSWORD')
    if encoded is not None:
        if not valid_hash(encoded): raise ValueError('Invalid BRIGHTCLEAN_ADMIN_PASSWORD_HASH format')
        return username, encoded, False
    return username, hash_password(password if password else 'admin-change-me'), not bool(password)

class Problem(Exception):
    def __init__(self, status, message): self.status, self.message = status, message

def require(condition, status=400, message='Invalid input'):
    if not condition: raise Problem(status, message)

class Application:
    def __init__(self, root, username, password_hash, classroom=False):
        self.root, self.username, self.password_hash = Path(root), username, password_hash
        crm = SoloCRM(self.root/'data/class3-demo-crm.db')
        organization = crm.create_organization(
            'BrightClean Classroom Demo',
            slug='brightclean-classroom-demo',
        )
        crm.create_website(
            SITE,
            name='BrightClean San Jose',
            organization_id=organization['id'],
        )
        self.classroom = classroom
        self.sessions = {}
        self.failures = []
        self.lock = threading.RLock()
    def settings(self,method,payload):
        target=self.root/'data/site-settings.json'
        if method=='GET': return 200,read_json(target,default_settings())
        require(method in ('PUT','POST'),405,'Method not allowed')
        value=validate_settings(payload); atomic_json(target,value); return 200,value
    def llm(self,method,payload,test=False):
        target=self.root/'data/llm-settings.json'; current=read_json(target,default_llm_settings()); key=read_api_key(self.root)
        if test:
            require(method=='POST',405,'Method not allowed'); require(bool(key),400,'Configure an API key first')
            request=Request(current['base_url'].rstrip('/')+'/models',headers={'Authorization':'Bearer '+key,'Accept':'application/json'})
            try:
                with urlopen(request,timeout=8) as response: require(200<=response.status<300,502,'OpenAI connection failed')
            except Problem: raise
            except Exception: raise Problem(502,'Connection failed. Check the key, base URL, and network.')
            return 200,{'ok':True,'message':'Connection successful'}
        if method=='GET':
            suffix=('••••'+key[-4:]) if key else ''
            return 200,{'provider':'OpenAI','model':current.get('model','gpt-4o-mini'),'base_url':current.get('base_url','https://api.openai.com/v1'),'configured':bool(key),'masked_key':suffix,'restart_required':bool(current.get('restart_required',False)),'model_options':list(MODELS)}
        require(method in ('PUT','POST'),405,'Method not allowed'); value=validate_llm(payload)
        if payload.get('clear_key'):
            try: (self.root/'data/secrets/openai.env').unlink()
            except FileNotFoundError: pass
        elif payload.get('api_key'): save_api_key(self.root,payload['api_key'])
        atomic_json(target,value); return self.llm('GET',{})
    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.root/'data/class3-demo-crm.db', timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()
    def crm(self, method, table, ident, payload):
        fields = FIELDS[table]
        require(not set(payload) - set(fields), message='Unknown or protected field')
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as db:
            site = db.execute('SELECT id, organization_id FROM websites WHERE site_id=?',(SITE,)).fetchone()
            require(site is not None, 503, 'Demo CRM site is missing; run reset-demo.sh')
            site_id, org_id = site
            existing = None
            if ident:
                existing = db.execute(f'SELECT * FROM {table} WHERE id=? AND website_id=?',(ident,site_id)).fetchone()
                require(existing is not None,404,'Record not found')
            if method == 'GET':
                return 200, dict(existing) if existing else [dict(r) for r in db.execute(f'SELECT * FROM {table} WHERE website_id=? ORDER BY id DESC',(site_id,))]
            if method == 'DELETE':
                require(ident,400)
                db.execute(f'DELETE FROM {table} WHERE id=? AND website_id=?',(ident,site_id))
                return 200, {'ok':True}
            require(method in ('POST','PUT') and (method == 'POST') != bool(ident),405,'Method not allowed')
            values = {k:existing[k] if existing else v for k,v in fields.items()}
            values.update(payload)
            for key,value in values.items():
                if key in ('contact_id','deal_id'):
                    require(value is None or type(value) is int)
                    if value is not None:
                        linked = 'contacts' if key == 'contact_id' else 'deals'
                        require(db.execute(f'SELECT id FROM {linked} WHERE id=? AND website_id=?',(value,site_id)).fetchone() is not None,message='Related record must belong to this site')
                elif key in ('value','probability','completed'):
                    require(type(value) in (int,float) and math.isfinite(value) and value >= 0)
                    if key == 'probability': require(type(value) is int and value <= 100)
                    if key == 'completed': require(type(value) is int and value in (0,1))
                else:
                    require(isinstance(value,str) and len(value)<=10000)
                    values[key]=value.strip()
            required = {'contacts':'name','deals':'title','activities':'body'}[table]
            require(bool(values[required]),message=f'{required.title()} is required')
            if table=='contacts' and values['email']: require('@' in values['email'] and ' ' not in values['email'],message='Enter a valid email')
            if table=='deals': require(len(values['currency'])==3 and values['currency'].isalpha(),message='Use a three-letter currency code')
            for field in ('close_date','follow_up_at'):
                if values.get(field):
                    try: datetime.fromisoformat(values[field])
                    except ValueError: raise Problem(400,'Enter a valid ISO date')
            if table != 'activities': values['updated_at']=now
            if existing:
                db.execute(f'UPDATE {table} SET '+','.join(f'{k}=?' for k in values)+' WHERE id=? AND website_id=?',(*values.values(),ident,site_id))
            else:
                values.update(website_id=site_id, organization_id=org_id, created_at=now)
                if table == 'activities': values['happened_at']=now
                cursor=db.execute(f'INSERT INTO {table} ('+','.join(values)+') VALUES ('+','.join('?' for _ in values)+')',tuple(values.values()))
                ident=cursor.lastrowid
            return (200 if existing else 201),dict(db.execute(f'SELECT * FROM {table} WHERE id=?',(ident,)).fetchone())
    def rag(self, method, ident, payload):
        require(not set(payload)-{'title','content','url','site_id'},message='Unknown or protected field')
        doc=json.loads((self.root/'data/rag-content.json').read_text())
        rows=doc.setdefault('sites',{}).setdefault(SITE,[])
        existing=next((r for r in rows if r['content_id']==ident),None)
        if ident: require(existing is not None,404,'Knowledge item not found')
        if method=='GET': return 200,existing if ident else rows
        if method=='DELETE':
            require(ident)
            rows.remove(existing)
            result={'ok':True}
        else:
            require(method in ('POST','PUT') and (method=='POST') != bool(ident),405,'Method not allowed')
            values={k:payload.get(k,(existing or {}).get(k,'')) for k in ('title','content','url')}
            require(all(isinstance(v,str) and len(v)<=50000 for v in values.values()))
            require(values['title'].strip() and values['content'].strip(),message='Title and content are required')
            require(not values['url'] or urlsplit(values['url']).scheme in ('http','https'),message='URL must use http or https')
            now=int(time.time())
            if not existing:
                existing={'content_id':'rag_'+secrets.token_hex(8),'created_at':now}
                rows.append(existing)
            existing.update(values,updated_at=now)
            result=existing
        target=self.root/'data/rag-content.json'
        temporary=target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(doc,indent=2)+'\n')
        os.replace(temporary,target)
        return (201 if method=='POST' else 200),result

class Handler(BaseHTTPRequestHandler):
    server_version='BrightClean'
    def log_message(self,*args): pass  # Do not log credentials, cookies or request bodies.
    def send(self,status,data,headers=None,ctype='application/json; charset=utf-8'):
        body=json.dumps(data).encode() if ctype.startswith('application/json') else data
        self.send_response(status)
        for key,value in {'Content-Type':ctype,'Content-Length':str(len(body)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",**(headers or {})}.items(): self.send_header(key,value)
        self.end_headers(); self.wfile.write(body)
    def handle_request(self):
        app=self.server.app
        try:
            allowed_hosts={f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            require(self.headers.get('Host') in allowed_hosts,403,'Invalid host')
            origin=self.headers.get('Origin')
            require(not origin or origin in {'http://'+h for h in allowed_hosts},403,'Invalid origin')
            parsed=urlsplit(self.path); path=parsed.path; method=self.command
            if method=='GET' and path in ('/','/app.js','/style.css'):
                file={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
                self.send(200,(app.root/'admin'/file).read_bytes(),ctype={'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[path]); return
            payload={}
            if method!='GET':
                require(self.headers.get('Content-Type','').split(';')[0]=='application/json',415,'JSON required')
                try: length=int(self.headers.get('Content-Length','0'))
                except ValueError: raise Problem(400,'Invalid length')
                require(0<=length<=131072,413,'Request too large')
                try: payload=json.loads(self.rfile.read(length) or b'{}')
                except (ValueError,UnicodeError): raise Problem(400,'Invalid JSON')
                require(isinstance(payload,dict))
            with app.lock:
                now=time.time()
                app.sessions={k:v for k,v in app.sessions.items() if v['expires']>now}
                if path=='/api/login' and method=='POST':
                    app.failures=[t for t in app.failures if now-t<60]
                    require(len(app.failures)<10,429,'Too many attempts. Try again in a minute.')
                    username=payload.get('username',''); password=payload.get('password','')
                    require(isinstance(username,str) and isinstance(password,str) and len(password)<=1024)
                    password_ok=verify_password(password,app.password_hash)
                    if not (hmac.compare_digest(username.encode(),app.username.encode()) and password_ok):
                        app.failures.append(now); raise Problem(401,'Invalid username or password')
                    token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(32)
                    app.sessions[token]={'csrf':csrf,'expires':now+TTL}
                    self.send(200,{'csrf':csrf}, {'Set-Cookie':f'brightclean_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={TTL}'}); return
                cookie=SimpleCookie()
                try: cookie.load(self.headers.get('Cookie',''))
                except Exception: pass
                token=cookie['brightclean_session'].value if 'brightclean_session' in cookie else ''
                session=app.sessions.get(token)
                require(session is not None,401,'Sign in to continue')
                if method!='GET': require(hmac.compare_digest(self.headers.get('X-CSRF-Token','').encode(),session['csrf'].encode()),403,'CSRF token missing or invalid')
                if path=='/api/session' and method=='GET':
                    self.send(200,{'csrf':session['csrf'],'username':app.username,'classroom':app.classroom,'expires':session['expires']}); return
                if path=='/api/logout' and method=='POST':
                    del app.sessions[token]
                    self.send(200,{'ok':True},{'Set-Cookie':'brightclean_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'}); return
                require((path=='/api/settings' or payload.get('site_id',SITE)==SITE) and all(v==SITE for v in parse_qs(parsed.query).get('site_id',[])),403,'Site is outside this demo')
                parts=path.strip('/').split('/')
                require(len(parts) in (2,3) and parts[0]=='api',404,'Not found')
                resource=parts[1]; ident=parts[2] if len(parts)==3 else None
                if resource=='settings' and ident is None: status,data=app.settings(method,payload)
                elif resource=='llm' and ident in (None,'test'): status,data=app.llm(method,payload,ident=='test')
                elif resource=='rag': status,data=app.rag(method,ident,payload)
                elif resource in FIELDS:
                    require(ident is None or ident.isdigit(),404,'Not found')
                    status,data=app.crm(method,resource,int(ident) if ident else None,payload)
                elif resource=='summary' and method=='GET':
                    status=200
                    data={k:len(app.crm('GET',k,None,{})[1]) for k in FIELDS}
                    data['knowledge']=len(app.rag('GET',None,{})[1])
                else: raise Problem(404,'Not found')
                self.send(status,data)
        except Problem as exc: self.send(exc.status,{'error':exc.message})
        except (sqlite3.Error,OSError,ValueError,KeyError): self.send(503,{'error':'Data unavailable. Check local server setup and try again.'})
    do_GET=do_POST=do_PUT=do_DELETE=handle_request

def make_server(app,port=8200):
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.app=app
    return server

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--hash-password',action='store_true')
    args=parser.parse_args()
    if args.hash_password:
        password=getpass.getpass('New admin password: ')
        if not password or password!=getpass.getpass('Confirm password: '): raise SystemExit('Passwords must match and cannot be empty')
        print(hash_password(password)); return
    username,encoded,classroom=credentials()
    if classroom: print(f'CLASSROOM DEFAULT: {username}/admin-change-me (localhost only). Set environment credentials for private use.',flush=True)
    server=make_server(Application(ROOT,username,encoded,classroom))
    print('Admin: http://127.0.0.1:8200/',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
