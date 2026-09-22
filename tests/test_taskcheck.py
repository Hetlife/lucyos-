import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from tests.base import AionTest
from aion_core import db, taskcheck, tasks

class TestTaskCheck(AionTest):
    def setUp(self):
        super().setUp(); taskcheck.load_builtin_templates()
    def make(self):
        return taskcheck.create_task(template_id='used_camera_insta360_go2',title='Used Insta360 GO 2 inspection',description='Inspect before payment',requester='Het',assignee='Aksh',location='Mumbai, India',metadata={'item':'used Insta360 GO 2','asking_price_display':'₹8,000'},public_base_url='https://taskcheck.example.test')
    def test_lifecycle_reuses_aion_task_and_events(self):
        created=self.make(); self.assertTrue(created['access_token']); self.assertIn('/t/',created['url']); row=tasks.get(created['aion_task_id']); self.assertEqual(row['kind'],'taskcheck'); self.assertEqual(row['status'],'WAITING')
        token=created['access_token']; public=taskcheck.public_task(token); self.assertEqual(len(public['checks']),14)
        for c in public['checks']:
            response='SKIP' if c['id'] in ('activation_account','accessories') else ('FAIL' if c['id']=='battery' else 'PASS')
            taskcheck.answer_check(token,c['id'],response,'Short field note' if response!='PASS' else '')
        ev=taskcheck.add_evidence(token,'battery',b'fake-image-bytes','image/jpeg'); self.assertTrue(Path(taskcheck.evidence_root()/created['taskcheck_id']/(ev['evidence_id']+'.jpg')).exists())
        report=taskcheck.complete(token); self.assertEqual(report['result_status'],'HOLD_PAYMENT'); self.assertEqual(report['counts']['PASS'],11); self.assertEqual(report['counts']['FAIL'],1); self.assertEqual(report['counts']['SKIP'],2); self.assertEqual(tasks.get(created['aion_task_id'])['status'],'NEEDS_REVIEW')
        reviewed=taskcheck.review(created['taskcheck_id'],'Het'); self.assertEqual(reviewed['status'],'REVIEWED'); self.assertEqual(tasks.get(created['aion_task_id'])['status'],'DONE')
        kinds=[r['kind'] for r in db.connect().execute("SELECT kind FROM events WHERE subject=?",(created['taskcheck_id'],))]; self.assertIn('task.created',kinds); self.assertIn('task.assigned',kinds); self.assertIn('task.completed',kinds); self.assertIn('task.reviewed',kinds)
    def test_required_checks_block_submission(self):
        created=self.make(); with_token=created['access_token']; taskcheck.answer_check(with_token,'power_on','PASS')
        with self.assertRaises(ValueError): taskcheck.complete(with_token)
    def test_token_is_hashed_and_revocable(self):
        created=self.make(); row=db.connect().execute('SELECT access_token_hash FROM taskcheck_runs WHERE taskcheck_id=?',(created['taskcheck_id'],)).fetchone(); self.assertNotEqual(row['access_token_hash'],created['access_token']); taskcheck.revoke(created['taskcheck_id'])
        with self.assertRaises(ValueError): taskcheck.public_task(created['access_token'])
    def test_report_is_factual(self):
        created=self.make(); msg=taskcheck.whatsapp_assignment(taskcheck.public_task(created['access_token'],mark_opened=False),created['url']); self.assertIn('PASS / FAIL / SKIP',msg); self.assertNotIn('buy it',msg.lower()); self.assertNotIn('do not buy',msg.lower())
