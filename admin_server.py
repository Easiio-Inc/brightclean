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
import io
import mimetypes
import zipfile
import xml.etree.ElementTree as ET
from email.parser import BytesParser
from email.policy import default as email_policy
from urllib.parse import urlsplit, parse_qs
from urllib.request import Request, urlopen

from backend.crm_core import SoloCRM

ROOT = Path(__file__).resolve().parent
SITE = 'class3-brightclean-san-jose'
MAX_UPLOAD_BYTES = int(os.environ.get('EASIIO_RAG_UPLOAD_MAX_BYTES', str(10*1024*1024)))
MAX_ZIP_MEMBERS = int(os.environ.get('EASIIO_RAG_ZIP_MAX_MEMBERS','2000'))
MAX_ZIP_UNCOMPRESSED = int(os.environ.get('EASIIO_RAG_ZIP_MAX_UNCOMPRESSED',str(50*1024*1024)))
MAX_ZIP_MEMBER_BYTES = int(os.environ.get('EASIIO_RAG_ZIP_MAX_MEMBER_BYTES',str(10*1024*1024)))
MAX_ZIP_RATIO = int(os.environ.get('EASIIO_RAG_ZIP_MAX_RATIO','100'))
MAX_EXTRACTED_CHARS = int(os.environ.get('EASIIO_RAG_MAX_EXTRACTED_CHARS',str(2*1024*1024)))
MAX_PDF_PAGES = int(os.environ.get('EASIIO_RAG_MAX_PDF_PAGES','250'))
UPLOAD_EXTENSIONS={'.txt','.docx','.pptx','.pdf'}
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

def _safe_zip(data):
    try: archive=zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile,OSError): raise Problem(400,'Corrupt Office document')
    infos=archive.infolist()
    require(len(infos)<=MAX_ZIP_MEMBERS,400,'Office document has too many members')
    require(sum(i.file_size for i in infos)<=MAX_ZIP_UNCOMPRESSED,400,'Office document expands beyond the safe limit')
    require(all(not i.filename.startswith(('/', '\\')) and '..' not in Path(i.filename).parts for i in infos),400,'Unsafe Office document')
    require(all(not (i.flag_bits & 1) for i in infos),400,'Encrypted Office members are not supported')
    require(all(i.file_size<=MAX_ZIP_MEMBER_BYTES and i.file_size<=MAX_ZIP_RATIO*max(i.compress_size,1) for i in infos),400,'Office member exceeds safe size or compression ratio')
    names=[i.filename for i in infos]; require(len(names)==len(set(names)),400,'Duplicate Office members are not allowed')
    return archive

def parse_knowledge_file(filename,data):
    ext=Path(filename).suffix.lower(); require(ext in UPLOAD_EXTENSIONS,415,'Allowed types: PDF, DOCX, PPTX, TXT')
    if ext=='.txt':
        require(b'\x00' not in data,400,'TXT appears to be binary')
        try: text=data.decode('utf-8-sig')
        except UnicodeDecodeError: raise Problem(400,'TXT must be UTF-8 encoded')
        require(bool(text.strip()),400,'Document contains no text'); return text,{'pages':1}
    if ext in ('.docx','.pptx'):
        archive=_safe_zip(data); require('[Content_Types].xml' in archive.namelist(),400,'Invalid Office container')
        try: content_types=ET.fromstring(archive.read('[Content_Types].xml'))
        except ET.ParseError: raise Problem(400,'Corrupt Office content types')
        expected=('/word/document.xml','application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml') if ext=='.docx' else ('/ppt/presentation.xml','application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml')
        overrides={(node.attrib.get('PartName'),node.attrib.get('ContentType')) for node in content_types if node.tag.endswith('}Override') or node.tag=='Override'}
        require(expected in overrides,400,f'Invalid {ext[1:].upper()} main-part content type')
        if ext=='.docx':
            require('word/document.xml' in archive.namelist(),400,'DOCX document body is missing')
            try: root=ET.fromstring(archive.read('word/document.xml'))
            except ET.ParseError: raise Problem(400,'Corrupt DOCX XML')
            paragraphs=[]
            for paragraph in root.iter():
                if paragraph.tag.endswith('}p'):
                    value=''.join(n.text or '' for n in paragraph.iter() if n.tag.endswith('}t')).strip()
                    if value: paragraphs.append(value)
            require(paragraphs,400,'DOCX contains no extractable text'); return '\n\n'.join(paragraphs),{'pages':1}
        names=sorted((n for n in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)),key=lambda n:int(re.search(r'\d+',Path(n).name).group()))
        require(names,400,'PPTX contains no slides'); slides=[]
        for number,name in enumerate(names,1):
            try: root=ET.fromstring(archive.read(name))
            except ET.ParseError: raise Problem(400,'Corrupt PPTX XML')
            values=[n.text.strip() for n in root.iter() if n.tag.endswith('}t') and n.text and n.text.strip()]
            if values: slides.append(f"Slide {number}\n"+'\n'.join(values))
        require(slides,400,'PPTX contains no extractable text'); return '\n\n'.join(slides),{'pages':len(names)}
    require(data.startswith(b'%PDF-'),400,'Invalid PDF signature')
    try: import fitz
    except (ImportError,ModuleNotFoundError): raise Problem(503,'PDF extraction requires PyMuPDF; install requirements-rag.txt')
    try:
        with fitz.open(stream=data,filetype='pdf') as doc:
            require(not doc.needs_pass,400,'Encrypted PDFs are not supported')
            require(len(doc)<=MAX_PDF_PAGES,413,'PDF exceeds the configured page limit')
            pages=[]; extracted=0
            for i,page in enumerate(doc):
                page_text=page.get_text().strip(); extracted+=len(page_text)
                require(extracted<=MAX_EXTRACTED_CHARS,413,'Extracted text exceeds the configured limit')
                if page_text: pages.append(f"Page {i+1}\n{page_text}")
    except Problem: raise
    except Exception: raise Problem(400,'Corrupt PDF')
    require(pages,422,'PDF has no extractable text; scanned PDFs require OCR and are not supported')
    return '\n\n'.join(pages),{'pages':len(pages)}

def chunk_document(document_id,text,size=1400,overlap=180):
    require(size>0 and 0<=overlap<size,message='Invalid chunk settings')
    chunks=[]; step=size-overlap
    for start in range(0,len(text),step):
        value=text[start:start+size]
        if not value: break
        digest=hashlib.sha256(value.encode()).hexdigest()
        chunks.append({'chunk_id':f'{document_id}:{len(chunks)}:{digest[:12]}','text':value,'content_hash':digest})
        if start+size>=len(text): break
    return chunks

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
        if existing and existing.get('upload_id') and method in ('PUT','DELETE'):
            raise Problem(409,f"Uploaded knowledge must be deleted with /api/uploads/{existing['upload_id']}")
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
    def _upload_manifest(self): return self.root/'data/knowledge-files'/SITE/'manifest.json'
    def _read_uploads(self): return read_json(self._upload_manifest(),{'uploads':[]}).get('uploads',[])
    def upload_knowledge(self,site_id,filename,data):
        require(site_id==SITE,403,'Site is outside this demo'); require(isinstance(data,bytes) and len(data)<=MAX_UPLOAD_BYTES,413,'Upload exceeds configured limit')
        original=str(filename); require(original==Path(original).name and '/' not in original and '\\' not in original,400,'Filename must not contain a path')
        text,details=parse_knowledge_file(original,data); require(len(text)<=MAX_EXTRACTED_CHARS,413,'Extracted text exceeds the configured limit')
        upload_id='upl_'+secrets.token_hex(12); ext=Path(original).suffix.lower(); stored=upload_id+ext
        source_link=f'/api/uploads/{upload_id}/file'; chunks=chunk_document('upload:'+upload_id,text); now=int(time.time())
        content_hash=hashlib.sha256(text.encode()).hexdigest()
        item={'content_id':'upload:'+upload_id,'document_id':'upload:'+upload_id,'title':Path(original).stem[:300] or 'Uploaded document','url':source_link,'content':text,'source':'upload','upload_id':upload_id,'original_filename':original,'mime_type':mimetypes.guess_type(original)[0] or 'application/octet-stream','file_sha256':hashlib.sha256(data).hexdigest(),'content_sha256':content_hash,'content_hash':content_hash,'chunk_count':len(chunks),'created_at':now,'updated_at':now}
        target=self.root/'data/rag-content.json'; doc=read_json(target,{'version':1,'sites':{}}); doc.setdefault('sites',{}).setdefault(SITE,[]).append(item)
        directory=self.root/'data/knowledge-files'/SITE; path=directory/stored; manifest=self._upload_manifest(); records=self._read_uploads(); record={**item,'stored_filename':stored,'size':len(data),**details}; records.append(record)
        directory.mkdir(parents=True,exist_ok=True); old_target=target.read_bytes() if target.exists() else None; old_manifest=manifest.read_bytes() if manifest.exists() else None
        try:
            temporary=path.with_name(path.name+'.tmp'); temporary.write_bytes(data); os.replace(temporary,path)
            atomic_json(target,doc); atomic_json(manifest,{'version':1,'uploads':records})
        except Exception:
            for temp in directory.glob('*.tmp'): temp.unlink(missing_ok=True)
            path.unlink(missing_ok=True)
            if old_target is None: target.unlink(missing_ok=True)
            else: target.write_bytes(old_target)
            if old_manifest is None: manifest.unlink(missing_ok=True)
            else: manifest.write_bytes(old_manifest)
            raise
        indexed=False; warning='Vector indexing is not configured; JSON search remains available.'
        try:
            from backend.rag_store import configured_store
            store=configured_store()
            if store:
                store.ingest(SITE,{'document_id':item['content_id'],'upload_id':upload_id,'title':item['title'],'content':text,'content_hash':content_hash,'chunks':chunks,'source_url':source_link,'original_filename':original,'stored_filename':stored,'mime_type':item['mime_type'],'metadata':{'upload_id':upload_id}}); indexed=True; warning=''
        except Exception:
            warning='Vector indexing failed; JSON search remains available.'
        public={k:v for k,v in record.items() if k!='stored_filename'}
        return {**public,'source_link':source_link,'document_count':1,'indexed':indexed,'index_warning':warning}
    def download_upload(self,site_id,upload_id):
        require(site_id==SITE,403,'Site is outside this demo')
        row=next((x for x in self._read_uploads() if x.get('upload_id')==upload_id),None); require(row is not None,404,'Upload not found')
        base=(self.root/'data/knowledge-files'/SITE).resolve(); path=base/row['stored_filename']
        require(not path.is_symlink() and path.is_file() and path.resolve().parent==base,404,'Upload not found')
        return path.read_bytes(),row['original_filename'],row['mime_type']
    def delete_upload(self,site_id,upload_id):
        require(site_id==SITE,403,'Site is outside this demo'); records=self._read_uploads(); row=next((x for x in records if x.get('upload_id')==upload_id),None); require(row is not None,404,'Upload not found')
        target=self.root/'data/rag-content.json'; manifest=self._upload_manifest(); path=self.root/'data/knowledge-files'/SITE/row['stored_filename']
        doc=read_json(target,{'sites':{}}); rows=doc.setdefault('sites',{}).get(SITE,[]); doc['sites'][SITE]=[x for x in rows if x.get('upload_id')!=upload_id]
        try:
            from backend.rag_store import configured_store
            store=configured_store()
            if store: store.delete(SITE,row['content_id'])
        except Exception:
            raise Problem(503,'Vector index deletion failed; no files or records were deleted.')
        old_target=target.read_bytes(); old_manifest=manifest.read_bytes(); old_file=path.read_bytes() if path.exists() else None
        try:
            atomic_json(target,doc); atomic_json(manifest,{'version':1,'uploads':[x for x in records if x.get('upload_id')!=upload_id]}); path.unlink(missing_ok=True)
        except Exception:
            target.write_bytes(old_target); manifest.write_bytes(old_manifest)
            if old_file is not None: path.write_bytes(old_file)
            for temp in path.parent.glob('*.tmp'): temp.unlink(missing_ok=True)
            raise
        indexed=bool(store); warning='' if store else 'Vector index is not configured.'
        return {'ok':True,'upload_id':upload_id,'indexed':indexed,'index_warning':warning}

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
            payload={}; upload=None
            if method!='GET':
                content_type=self.headers.get('Content-Type','')
                try: length=int(self.headers.get('Content-Length','0'))
                except ValueError: raise Problem(400,'Invalid length')
                limit=MAX_UPLOAD_BYTES+65536 if content_type.startswith('multipart/form-data;') else 131072
                require(0<=length<=limit,413,'Request too large')
                # Reject unauthenticated/CSRF-invalid uploads before reading or parsing
                # potentially expensive multipart bodies.
                if content_type.startswith('multipart/form-data;'):
                    cookie=SimpleCookie()
                    try: cookie.load(self.headers.get('Cookie',''))
                    except Exception: pass
                    pretoken=cookie['brightclean_session'].value if 'brightclean_session' in cookie else ''
                    presession=app.sessions.get(pretoken)
                    require(presession is not None,401,'Sign in to continue')
                    require(hmac.compare_digest(self.headers.get('X-CSRF-Token','').encode(),presession['csrf'].encode()),403,'CSRF token missing or invalid')
                raw=self.rfile.read(length)
                if content_type.startswith('multipart/form-data;'):
                    try:
                        message=BytesParser(policy=email_policy).parsebytes((f'Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n').encode()+raw)
                        parts=list(message.iter_parts()); require(len(parts)<=10,400,'Too many multipart fields')
                        files=[p for p in parts if p.get_filename() is not None]; require(len(files)==1,400,'Exactly one file is required')
                        upload=(files[0].get_filename(),files[0].get_payload(decode=True) or b'')
                        payload={p.get_param('name',header='content-disposition'):p.get_content() for p in parts if p.get_filename() is None and p.get_param('name',header='content-disposition')}
                    except Problem: raise
                    except Exception: raise Problem(400,'Invalid multipart upload')
                else:
                    require(content_type.split(';')[0]=='application/json',415,'JSON or multipart form data required')
                    try: payload=json.loads(raw or b'{}')
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
                upload_match=re.fullmatch(r'/api/uploads/([A-Za-z0-9_]+)/file',path)
                delete_match=re.fullmatch(r'/api/uploads/([A-Za-z0-9_]+)',path)
                if path=='/api/uploads' and method=='POST':
                    require(upload is not None,400,'File is required'); data=app.upload_knowledge(SITE,upload[0],upload[1]); self.send(201,data); return
                if path=='/api/uploads' and method=='GET': self.send(200,{'items':app._read_uploads()}); return
                if upload_match and method=='GET':
                    data,name,mime=app.download_upload(SITE,upload_match.group(1)); safe_name=re.sub(r'[^A-Za-z0-9._ -]','_',name)
                    self.send(200,data,{'Content-Disposition':f'attachment; filename="{safe_name}"'},ctype=mime); return
                if delete_match and method=='DELETE': self.send(200,app.delete_upload(SITE,delete_match.group(1))); return
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
