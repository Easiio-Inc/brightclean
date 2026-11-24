#!/usr/bin/env python3
"""Public allowlist wrapper around the repository-local chatbot backend.
Only chat/session/lead intake can write CRM as part of public conversation.
No public CRM browsing or administration routes are forwarded.
"""
import argparse
import importlib.util
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parent
SITE='class3-brightclean-san-jose'

def load_llm_environment(root=ROOT):
    from admin_server import read_json, default_llm_settings, read_api_key
    value=read_json(Path(root)/'data/llm-settings.json',default_llm_settings()); key=read_api_key(root)
    if key: os.environ['EASIIO_CHATBOT_LLM_API_KEY']=key
    else: os.environ.pop('EASIIO_CHATBOT_LLM_API_KEY',None)
    os.environ['EASIIO_CHATBOT_LLM_MODEL']=value.get('model','gpt-4o-mini')
    os.environ['EASIIO_CHATBOT_LLM_BASE_URL']=value.get('base_url','https://api.openai.com/v1')

def widget_config(root=ROOT):
    from admin_server import read_json, default_settings, LEAD_FIELDS
    value=read_json(Path(root)/'data/site-settings.json',default_settings()); a=value['appearance']; b=value['behavior']; business=value['business']; lead=value['lead_form']
    fields=[]
    for item in lead['fields']:
        label,kind,autocomplete=LEAD_FIELDS[item['name']]; fields.append({'name':item['name'],'label':label,'type':kind,'required':item['required'],'autocomplete':autocomplete})
    return {'siteId':SITE,'enabled':a['enabled'],'title':a['title'],'greeting':a['greeting'],'primaryColor':a['primary_color'],'position':a['position'],'launcherStyle':a['launcher_style'],'launcherSize':a['launcher_size'],'avatarUrl':a['avatar_url'],'autoOpen':b['auto_open'],'autoOpenDelaySeconds':b['auto_open_delay_seconds'],'trackPageViews':b['track_page_views'],'excludePaths':b['exclude_paths'],'organizationName':business['organization_name'],'websiteName':business['website_name'],'phone':business['phone'],'email':business['email'],'consentText':business['consent_text'],'leadFormsEnabled':lead['enabled'],'leadFormConfig':{'title':lead['title'],'help_text':lead['description'],'submit_label':lead['submit_label'],'fields':fields},'ragAdminEnabled':False}

def public_allowed(method,path):
    path=urlsplit(path).path
    return (method,path) in {('GET','/health'),('GET','/widget-config'),('GET','/api/chat/form-config'),('POST','/api/chat/session'),('POST','/api/chat/message'),('POST','/api/chat/lead')}

def static_allowed(path):
    path=unquote(urlsplit(path).path)
    if any(p in ('.','..') or p.startswith('.') for p in path.split('/') if p): return False
    if path in ('/','/index.html'): return True
    target=(ROOT/path.lstrip('/')).resolve()
    return path.startswith('/assets/') and target.is_relative_to(ROOT/'assets') and target.is_file()

def public_payload(payload):
    # Visitor messages are untrusted; website identity and knowledge are local.
    payload=dict(payload)
    payload['site_id']='class3-brightclean-san-jose'
    payload['organization_name']='BrightClean San Jose'
    payload['website_name']='BrightClean San Jose'
    payload['page_url']='http://127.0.0.1:8188/'
    payload['page_title']='BrightClean San Jose'
    payload['domain']='127.0.0.1:8188'
    payload['page_context']={
        'url':'http://127.0.0.1:8188/', 'title':'BrightClean San Jose',
        'content':'', 'language':'en',
    }
    return payload

def public_response(payload):
    # The shared backend also serves classroom automation tools; their results,
    # identifiers and diagnostics are not part of this public widget's contract.
    fields={'ok','error','session_id','welcome_message','reply','answer_source',
            'lead_captured','show_lead_form','suggested_actions','sources','confidence',
            'config','fields','enabled','title','description','submit_label','service'}
    return {key:value for key,value in payload.items() if key in fields}

class StaticHandler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        if not static_allowed(self.path): self.send_error(404); return
        super().do_GET()
    def do_HEAD(self):
        if not static_allowed(self.path): self.send_error(404); return
        super().do_HEAD()


def chatbot_server():
    # Keep every backend runtime store inside this checkout.
    for key,filename in {
        'FORM_CONFIG_STORE':'form-config.json','EMAIL_CONFIG_STORE':'email-config.json',
        'EMAIL_OUTBOX_DIR':'email-outbox','RAG_ANSWER_LOG':'rag-answer-log.json',
        'RAG_FEEDBACK_STORE':'rag-feedback.json','CLASS12_REVIEW_STORE':'review.json',
        'CLASS12_SKILL_DRAFT_DIR':'skill-drafts','CLASS12_PUBLISHED_SKILL_DIR':'published-skills',
        'CLASS12_HERMES_SKILL_DIR':'hermes-skills','RAG_SYNC_LOG':'rag-sync-log.json',
        'RAG_EXTERNAL_SOURCES':'rag-external-sources.json','RAG_REFRESH_SCHEDULE':'rag-refresh.json',
        'RAG_NOTIFICATIONS':'rag-notifications.json','VOICE_CACHE_DIR':'voice-cache',
    }.items():
        os.environ['EASIIO_CHATBOT_'+key]=str(ROOT/'.run'/filename)
    os.environ['EASIIO_DOCS_DB']=str(ROOT/'.run/docs.db')
    os.environ['EASIIO_WIKI_DB']=str(ROOT/'.run/wiki.db')
    os.environ['EASIIO_CHATBOT_RAG_DEBUG']='false'
    os.environ['EASIIO_CHATBOT_RAG_STORE']=str(ROOT/'data/rag-content.json')
    os.environ['SOLO_CRM_DB']=str(ROOT/'data/class3-demo-crm.db')
    os.environ['EASIIO_CHATBOT_ALLOWED_ORIGINS']='http://127.0.0.1:8188,http://localhost:8188'
    load_llm_environment(ROOT)
    sys.dont_write_bytecode=True
    source=ROOT/'backend'/'chatbot_app.py'
    spec=importlib.util.spec_from_file_location('brightclean_chatbot',source)
    backend=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=backend
    spec.loader.exec_module(backend)
    class PublicHandler(backend.ChatbotHandler):
        def handle_public(self):
            if self.headers.get('Host') not in ('127.0.0.1:8199','localhost:8199'):
                self._send(backend.json_response(403,{'error':'Invalid host'})); return
            if not public_allowed(self.command,self.path):
                self._send(backend.json_response(403,{'error':'Use authenticated admin on port 8200'})); return
            if self.command=='GET' and urlsplit(self.path).path=='/widget-config':
                self._send(backend.json_response(200,widget_config(ROOT))); return
            body=b''
            if self.command=='POST':
                import json
                try:
                    length=int(self.headers.get('Content-Length','0'))
                    if not 0<=length<=65536: raise ValueError()
                    payload=json.loads(self.rfile.read(length))
                    if not isinstance(payload,dict): raise ValueError()
                    payload=public_payload(payload)
                    body=json.dumps(payload).encode()
                except (ValueError,UnicodeError):
                    self._send(backend.json_response(400,{'error':'Invalid request'})); return
            path=self.path
            if self.command=='GET' and urlsplit(path).path=='/api/chat/form-config':
                path='/api/chat/form-config?site_id=class3-brightclean-san-jose'
            response=backend.route_request(self.command,path,dict(self.headers),body,self.server.crm)
            if isinstance(response.body,dict):
                response.body=public_response(response.body)
            self._send(response)
        do_GET=do_POST=do_PUT=do_DELETE=handle_public
        def do_OPTIONS(self):
            self._send(backend.json_response(204,{}))
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',8199),PublicHandler)
    server.crm=backend.SoloCRM(str(ROOT/'data/class3-demo-crm.db'))
    return server

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('service',choices=['website','chatbot'])
    args=parser.parse_args()
    server=chatbot_server() if args.service=='chatbot' else ThreadingHTTPServer(('127.0.0.1',8188),StaticHandler)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
