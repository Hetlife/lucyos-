import json, threading, unittest, urllib.request, urllib.error
from aion_core import taskcheck
from bridges.taskcheck_server import build_server
from tests.base import AionTest

class TestTaskCheckHTTP(AionTest):
    def setUp(self):
        super().setUp(); taskcheck.load_builtin_templates(); self.server=build_server('127.0.0.1',0); self.port=self.server.server_address[1]; self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.created=taskcheck.create_task(template_id='used_camera_insta360_go2',title='Used Insta360 GO 2 inspection',description='Inspect before payment',requester='Het',assignee='Aksh',location='Mumbai, India',metadata={'item':'used Insta360 GO 2','asking_price_display':'₹8,000'},public_base_url=f'http://127.0.0.1:{self.port}')
    def tearDown(self): self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2); super().tearDown()
    def fetch(self,path,method='GET',body=None,ctype='application/json'):
        data=None if body is None else (body if isinstance(body,bytes) else json.dumps(body).encode()); req=urllib.request.Request(f'http://127.0.0.1:{self.port}{path}',data=data,method=method,headers={'Content-Type':ctype}); return urllib.request.urlopen(req,timeout=3)
    def test_mobile_page_api_and_submit(self):
        tok=self.created['access_token']; html=self.fetch(f'/t/{tok}').read().decode(); self.assertIn('viewport-fit=cover',html); self.assertIn('og:title',html)
        task=json.loads(self.fetch(f'/api/taskcheck/{tok}').read())['task']; self.assertEqual(len(task['checks']),14)
        for c in task['checks']: self.fetch(f'/api/taskcheck/{tok}/check/{c["id"]}',method='POST',body={'response':'PASS','note':''}).read()
        ev=json.loads(self.fetch(f'/api/taskcheck/{tok}/evidence/body_lens',method='POST',body=b'jpeg-fixture',ctype='image/jpeg').read()); self.assertTrue(ev['evidence']['evidence_id'].startswith('EVD-'))
        report=json.loads(self.fetch(f'/api/taskcheck/{tok}/submit',method='POST',body={}).read())['report']; self.assertEqual(report['result_status'],'READY_FOR_REVIEW')
