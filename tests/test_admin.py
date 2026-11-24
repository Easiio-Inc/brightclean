import http.client
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import stat
import admin_server as a

ROOT = Path(__file__).resolve().parents[1]

class AdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / 'data', self.root / 'data')
        shutil.copytree(ROOT / 'admin', self.root / 'admin')
        self.app = a.Application(self.root, 'teacher', a.hash_password('test-password'))
        self.server = a.make_server(self.app, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.cookie = ''
        self.csrf = ''
    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()
    def req(self, method, path, data=None, csrf=True, origin=None):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        headers = {'Host': f'127.0.0.1:{self.server.server_port}', 'Cookie': self.cookie}
        if data is not None: headers['Content-Type'] = 'application/json'
        if csrf: headers['X-CSRF-Token'] = self.csrf
        if origin: headers['Origin'] = origin
        c.request(method, path, json.dumps(data) if data is not None else None, headers)
        r = c.getresponse()
        raw = r.read()
        result = json.loads(raw) if r.getheader('Content-Type','').startswith('application/json') else raw.decode()
        cookie = r.getheader('Set-Cookie')
        c.close()
        return r.status, result, cookie
    def login(self):
        status, data, cookie = self.req('POST', '/api/login', {'username':'teacher','password':'test-password'})
        self.assertEqual(status, 200)
        self.cookie = cookie.split(';')[0]
        self.csrf = data['csrf']
        return cookie
    def test_unauthenticated(self):
        for path in ['/api/rag','/api/contacts','/api/deals','/api/activities','/api/summary','/api/session']:
            for method in ['GET','POST','PUT','DELETE']:
                self.assertEqual(self.req(method,path,{})[0],401)
        self.assertNotIn('test-password', self.req('GET','/')[1])
    def test_login_logout_expiration(self):
        self.assertEqual(self.req('POST','/api/login',{'username':'teacher','password':'wrong'})[0],401)
        cookie = self.login()
        self.assertIn('HttpOnly',cookie)
        self.assertIn('SameSite=Strict',cookie)
        self.assertEqual(self.req('GET','/api/session')[0],200)
        self.assertEqual(self.req('POST','/api/logout',{},False)[0],403)
        self.assertEqual(self.req('POST','/api/logout',{})[0],200)
        self.assertEqual(self.req('GET','/api/contacts')[0],401)
        self.login()
        for session in self.app.sessions.values(): session['expires'] = time.time()-1
        self.assertEqual(self.req('GET','/api/contacts')[0],401)
    def test_csrf_and_origin(self):
        self.login()
        for method in ['POST','PUT','DELETE']:
            self.assertEqual(self.req(method,'/api/rag',{},False)[0],403)
        self.assertEqual(self.req('POST','/api/rag',{},origin='http://evil.test')[0],403)
    def test_rag_crud_tenant_scope(self):
        doc=json.loads((self.root/'data/rag-content.json').read_text())
        doc['sites']['other']=[{'content_id':'foreign','title':'Secret'}]
        (self.root/'data/rag-content.json').write_text(json.dumps(doc))
        self.login()
        self.assertEqual(self.req('GET','/api/rag?site_id=other')[0],403)
        self.assertEqual(self.req('POST','/api/rag',{'site_id':'other','title':'x','content':'x'})[0],403)
        status,row,_=self.req('POST','/api/rag',{'title':'New','content':'Knowledge','url':''})
        self.assertEqual(status,201)
        ident=row['content_id']
        self.assertEqual(self.req('PUT','/api/rag/'+ident,{'title':'Updated'})[0],200)
        self.assertIn('Updated',str(self.req('GET','/api/rag')[1]))
        self.assertEqual(self.req('DELETE','/api/rag/foreign',{})[0],404)
        self.assertEqual(self.req('DELETE','/api/rag/'+ident,{})[0],200)
        self.assertEqual(json.loads((self.root/'data/rag-content.json').read_text())['sites']['other'],doc['sites']['other'])
    def test_crm_crud_validation(self):
        self.login()
        for table,values,change in [('contacts',{'name':"O'Brien'; DROP TABLE contacts;--",'email':'a@example.com'},{'status':'customer'}),('deals',{'title':'Demo','value':125},{'stage':'won'}),('activities',{'body':'Call back','kind':'call'},{'completed':1})]:
            status,row,_=self.req('POST','/api/'+table,values)
            self.assertEqual(status,201,(table,row))
            ident=row['id']
            self.assertEqual(self.req('PUT',f'/api/{table}/{ident}',change)[0],200)
            self.assertTrue(any(r['id']==ident for r in self.req('GET','/api/'+table)[1]))
            self.assertEqual(self.req('DELETE',f'/api/{table}/{ident}',{})[0],200)
        self.assertEqual(self.req('POST','/api/contacts',{'name':''})[0],400)
        self.assertEqual(self.req('POST','/api/deals',{'title':'x','probability':101})[0],400)
        self.assertEqual(self.req('POST','/api/activities',{'body':'x','contact_id':999999})[0],400)
        self.assertEqual(self.req('POST','/api/contacts',{'name':'x','website_id':999})[0],400)
    def test_password_safety(self):
        first=a.hash_password('secret'); second=a.hash_password('secret')
        self.assertNotEqual(first,second)
        self.assertNotIn('secret', first)
        self.assertTrue(a.verify_password('secret',first))
        self.assertFalse(a.verify_password('wrong',first))
        self.assertFalse(a.verify_password('secret','malformed'))
        with patch.dict(os.environ,{},clear=True):
            username,hashed,default=a.credentials()
            self.assertEqual(username,'admin'); self.assertTrue(default)
            self.assertTrue(a.verify_password('admin-change-me',hashed))
        with patch.dict(os.environ,{'BRIGHTCLEAN_ADMIN_USERNAME':'owner','BRIGHTCLEAN_ADMIN_PASSWORD_HASH':first},clear=True):
            self.assertEqual(a.credentials(),('owner',first,False))
        with patch.dict(os.environ,{'BRIGHTCLEAN_ADMIN_PASSWORD_HASH':'broken'},clear=True):
            with self.assertRaises(ValueError): a.credentials()
    def test_public_response_redacts_internal_results(self):
        from public_server import public_response
        result=public_response({'reply':'Hello','crm_contact_id':1,'email_agent':{'password':'secret'},'class12_result':{'path':'private'}})
        self.assertEqual(result,{'reply':'Hello'})
    def test_empty_configured_hash_fails_closed(self):
        with patch.dict(os.environ,{'BRIGHTCLEAN_ADMIN_PASSWORD_HASH':''},clear=True):
            with self.assertRaises(ValueError): a.credentials()
    def test_public_payload_isolation(self):
        from public_server import public_payload
        payload=public_payload({'site_id':'other','organization_name':'Other',
                                'page_context':{'content':'Poison','title':'Fake'},'message':'Hello'})
        self.assertEqual(payload['site_id'],a.SITE)
        self.assertNotIn('Poison', str(payload))
        self.assertEqual(payload['message'],'Hello')
    def test_host_validation_and_throttling(self):
        self.assertEqual(self.req('POST','/api/login',{},origin='http://evil.test')[0],403)
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        c.request('GET','/',headers={'Host':'evil.test'})
        r=c.getresponse(); self.assertEqual(r.status,403);r.read();c.close()
        self.app.failures=[time.time()]*10
        self.assertEqual(self.req('POST','/api/login',{'username':'teacher','password':'test-password'})[0],429)
    def test_crm_tenant_scope(self):
        self.login()
        with self.app.connection() as db:
            db.execute("INSERT INTO websites(site_id,name,created_at,updated_at) VALUES ('other','Other','','')")
            other=db.execute("SELECT id FROM websites WHERE site_id='other'").fetchone()[0]
            foreign=db.execute("INSERT INTO contacts(name,website_id,created_at,updated_at) VALUES ('Private',?,'','')",(other,)).lastrowid
        self.assertFalse(any(r['id']==foreign for r in self.req('GET','/api/contacts')[1]))
        self.assertEqual(self.req('PUT',f'/api/contacts/{foreign}',{'name':'Bad'})[0],404)
        self.assertEqual(self.req('DELETE',f'/api/contacts/{foreign}',{})[0],404)
        self.assertEqual(self.req('POST','/api/deals',{'title':'Bad link','contact_id':foreign})[0],400)
    def test_public_boundary(self):
        from public_server import public_allowed, static_allowed
        for method,path in [('GET','/api/rag/content'),('POST','/api/rag/content/delete'),('GET','/api/crm/contacts'),('POST','/api/chat/form-config')]:
            self.assertFalse(public_allowed(method,path))
        self.assertTrue(public_allowed('POST','/api/chat/message'))
        for path in ['/data/rag-content.json','/data/class3-demo-crm.db','/.git/config','/admin/app.js','/assets/../data/rag-content.json']:
            self.assertFalse(static_allowed(path))
        self.assertTrue(static_allowed('/assets/js/easiio-chatbot-widget.js'))

    def test_phase_a_settings_auth_validation_and_tenant(self):
        self.assertEqual(self.req('GET','/api/settings')[0],401)
        self.login(); settings=self.req('GET','/api/settings')[1]
        self.assertEqual(settings['site_id'],a.SITE); self.assertEqual(settings['appearance']['primary_color'],'#123d3a')
        settings['appearance']['title']='Clean Team'; settings['site_id']='other'
        status,saved,_=self.req('PUT','/api/settings',settings)
        self.assertEqual(status,200); self.assertEqual(saved['site_id'],a.SITE)
        self.assertEqual(json.loads((self.root/'data/site-settings.json').read_text())['appearance']['title'],'Clean Team')
        self.assertFalse((self.root/'data/site-settings.json.tmp').exists())
        self.assertEqual(self.req('PUT','/api/settings',settings,False)[0],403)
        for section,key,value in [('appearance','primary_color','red'),('appearance','position','middle'),('appearance','avatar_url','javascript:x'),('behavior','auto_open_delay_seconds',999),('business','website_url','file:///x')]:
            bad=json.loads(json.dumps(settings)); bad[section][key]=value
            self.assertEqual(self.req('PUT','/api/settings',bad)[0],400,(section,key))
        bad=json.loads(json.dumps(settings)); bad['lead_form']['fields']=[{'name':'password','required':True}]
        self.assertEqual(self.req('PUT','/api/settings',bad)[0],400)

    def test_phase_a_llm_secret_lifecycle(self):
        self.login(); data=self.req('GET','/api/llm')[1]
        self.assertFalse(data['configured']); self.assertNotIn('api_key',data)
        self.assertEqual(self.req('PUT','/api/llm',{'model':'../bad','base_url':'https://api.openai.com/v1','api_key':'sk-example-modern_1234567890'})[0],400)
        status,data,_=self.req('PUT','/api/llm',{'model':'gpt-4.1-mini','base_url':'https://api.openai.com/v1','api_key':'sk-example-modern_1234567890'})
        self.assertEqual(status,200); self.assertTrue(data['configured']); self.assertNotIn('api_key',data)
        secret=self.root/'data/secrets/openai.env'
        self.assertEqual(stat.S_IMODE(secret.stat().st_mode),0o600)
        self.req('PUT','/api/llm',{'model':'gpt-4o','base_url':'https://api.openai.com/v1','api_key':''})
        self.assertIn('sk-example-modern_1234567890',secret.read_text())
        self.req('PUT','/api/llm',{'model':'gpt-4o','base_url':'https://api.openai.com/v1','clear_key':True})
        self.assertFalse(secret.exists())

    def test_phase_a_llm_test_connection_mocked(self):
        self.login(); self.req('PUT','/api/llm',{'model':'gpt-4o-mini','base_url':'https://api.openai.com/v1','api_key':'sk-test_abcdefghijklmnop'})
        response=unittest.mock.MagicMock(); response.status=200; response.__enter__.return_value=response
        with patch('admin_server.urlopen',return_value=response) as call:
            status,data,_=self.req('POST','/api/llm/test',{})
            self.assertEqual((status,data),(200,{'ok':True,'message':'Connection successful'})); self.assertEqual(call.call_args.kwargs['timeout'],8)
        with patch('admin_server.urlopen',side_effect=OSError('failed with sk-secret-value')):
            status,data,_=self.req('POST','/api/llm/test',{})
            self.assertEqual(status,502); self.assertNotIn('sk-secret',str(data))

    def test_phase_a_public_config_and_runtime_environment(self):
        import public_server as p
        settings=a.default_settings(); settings['appearance']['title']='Remote title'
        (self.root/'data/site-settings.json').write_text(json.dumps(settings))
        result=p.widget_config(self.root)
        self.assertEqual(result['siteId'],a.SITE); self.assertEqual(result['title'],'Remote title')
        self.assertNotIn('api_key',json.dumps(result).lower()); self.assertFalse(result['ragAdminEnabled'])
        llm=a.default_llm_settings(); llm.update(model='gpt-4.1',base_url='https://example.test/v1')
        a.atomic_json(self.root/'data/llm-settings.json',llm); a.save_api_key(self.root,'sk-runtime_abcdefghijklmnop')
        with patch.dict(os.environ,{},clear=True):
            p.load_llm_environment(self.root)
            self.assertEqual(os.environ['EASIIO_CHATBOT_LLM_MODEL'],'gpt-4.1')
            self.assertEqual(os.environ['EASIIO_CHATBOT_LLM_API_KEY'],'sk-runtime_abcdefghijklmnop')

if __name__=='__main__': unittest.main()
