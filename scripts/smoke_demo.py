#!/usr/bin/env python3
"""Live HTTP smoke test. No secrets are printed; no admin records are mutated."""
import http.client
import json
import os
from pathlib import Path
import secrets
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def request(port,path,method='GET',payload=None,headers=None):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=30)
    headers={'Content-Type':'application/json',**(headers or {})}
    conn.request(method,path,json.dumps(payload) if payload is not None else None,headers)
    response=conn.getresponse()
    body=response.read()
    result=json.loads(body) if response.getheader('Content-Type','').startswith('application/json') else body.decode()
    cookie=response.getheader('Set-Cookie')
    conn.close()
    return response.status,result,cookie

def main():
    assert request(8188,'/')[0]==200
    assert 'data-rag-admin="false"' in request(8188,'/')[1]
    for path in ['/data/rag-content.json','/data/class3-demo-crm.db','/.git/config','/admin_server.py','/admin/index.html']:
        assert request(8188,path)[0]==404,path
    print('Website 8188: OK; private files denied')
    assert request(8199,'/health')[0]==200
    for path in ['/api/rag/content','/api/rag/content/delete','/api/crm/contacts']:
        for method in ['GET','POST']:
            assert request(8199,path,method,{})[0]==403,(path,method)
    visitor='admin-smoke-'+secrets.token_hex(4)
    status,session,_=request(8199,'/api/chat/session','POST',{'visitor_key':visitor})
    assert status==200,session
    status,answer,_=request(8199,'/api/chat/message','POST',{'visitor_key':visitor,'session_id':session.get('session_id',''),'message':'What is the standard cleaning hourly price?'})
    assert status==200,answer
    assert answer.get('reply') or answer.get('answer') or answer.get('message'), 'Missing chatbot reply'
    print('Chatbot 8199: OK; public conversation works; RAG/CRM routes denied')
    assert request(8200,'/')[0]==200
    assert request(8200,'/api/contacts')[0]==401
    username=os.environ.get('BRIGHTCLEAN_ADMIN_USERNAME','admin')
    password=os.environ.get('BRIGHTCLEAN_ADMIN_DEV_PASSWORD')
    if os.environ.get('BRIGHTCLEAN_ADMIN_PASSWORD_HASH'):
        import getpass
        password=getpass.getpass('Admin password for live smoke test: ')
    password=password or 'admin-change-me'
    status,session,cookie=request(8200,'/api/login','POST',{'username':username,'password':password})
    assert status==200,'Admin login failed'
    headers={'Cookie':cookie.split(';')[0]}
    assert 'HttpOnly' in cookie and 'SameSite=Strict' in cookie
    for path in ['/api/session','/api/summary','/api/contacts','/api/deals','/api/activities','/api/rag']:
        assert request(8200,path,headers=headers)[0]==200,path
    assert request(8200,'/api/rag','POST',{},headers)[0]==403
    headers['X-CSRF-Token']=session['csrf']
    assert request(8200,'/api/logout','POST',{},headers)[0]==200
    assert request(8200,'/api/session',headers=headers)[0]==401
    print('Admin 8200: OK; login, protected lists, CSRF denial and logout verified')

if __name__=='__main__': main()
