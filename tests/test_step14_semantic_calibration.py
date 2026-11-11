"""Offline prospective-arm integrity, selection and no-redispatch regression tests."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from src.evaluation import step14_semantic_calibration as c
from test_step14_queue_compatibility_pilot import body, recommendation


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        """Prevent all provider/network activity."""
        for method in ('connect','connect_ex'):
            mock=patch.object(socket.socket,method,side_effect=AssertionError('OFFLINE'));mock.start();self.addCleanup(mock.stop)

    def test_instruction_only_and_original_immutability(self):
        """Only prospective semantic instructions differ; original data remains unchanged."""
        original=body();original['instructions']=c.p.PROMPT;before=deepcopy(original)
        new=c.variant(original);c.comparable(original,new)
        self.assertEqual(original,before)
        for key in original:
            if key!='instructions':self.assertEqual(original[key],new[key])
        new['model']='different'
        with self.assertRaisesRegex(ValueError,'ARM_COMPARABILITY_DRIFT'):c.comparable(original,new)

    def test_deterministic_held_selection_excludes_development(self):
        """Hash strata are frozen without reference to baseline recommendation values."""
        rows=[dict(unitID=f'U{i:03}',tags=[('cross_family' if i%2 else 'within_family'),('sparse' if i%3 else 'dense'),
            ('instance_language' if i%5 else 'recorded_specificity_difference')]) for i in range(60)]
        excluded={x['unitID'] for x in rows[:16]}
        selected=c.select_held(rows,excluded)
        self.assertEqual(selected,c.select_held(list(reversed(rows)),excluded))
        self.assertEqual(len(selected),16);self.assertFalse({x['unitID'] for x in selected}&excluded)
        self.assertTrue({'cross_family','within_family','sparse','dense'} <= {t for x in selected for t in x['tags']})

    def test_exact_pair_alignment_and_transition_flags(self):
        """Changed and unchanged results remain distinct without gold judgments."""
        old=recommendation();new=deepcopy(old)
        new['assessments'][0].update(recommendation='abstain',identityLevel='unresolved',missingInformation=['version unknown'])
        rows=c.align(old,new,json.loads(body()['input']))
        self.assertTrue(rows[0]['categoryChanged']);self.assertFalse(rows[1]['categoryChanged'])
        self.assertIn('lost_same_entity_proposal_requires_inspection',rows[0]['reviewFlags'])
        new['assessments'][1]['pairID']='P1'
        with self.assertRaisesRegex(ValueError,'DUPLICATE_PAIR'):c.align(old,new,json.loads(body()['input']))

    def test_structural_validation_unchanged(self):
        """Both instruction arms retain the exact native endpoint citation gates."""
        request=body();request['instructions']=c.p.PROMPT
        for arm in (request,c.variant(request)):
            self.assertEqual(c.p.validate(recommendation(),arm)['assessedPairs'],2)
            bad=recommendation();bad['assessments'][0]['evidenceIDs']=['E3Q1']
            with self.assertRaisesRegex(ValueError,'FOREIGN_OR_UNKNOWN_EVIDENCE'):c.p.validate(bad,arm)

    def test_authority_hash_drift_stops_dry_run(self):
        """Frozen input drift is never waived by a prospective instruction variant."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run';root.mkdir();authority=Path(tmp)/'authority';authority.write_text('original')
            c.live.save(root/'manifest.json',dict(version=c.VERSION,inputHashes={str(authority):c.r.identity.sha(authority)},outputHashes={},cases={'development':[],'heldOut':[]}))
            with patch.object(c,'ROOT',Path(tmp)):
                c.verify(root);authority.write_text('changed')
                with self.assertRaises(ValueError):c.verify(root)

    def test_development_gate_never_runs_held_or_redispatches_unknown(self):
        """Separate stage gate and native durable intent survive an uncertain provider attempt."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=body();request['instructions']=c.p.PROMPT
            c.live.save(root/'development'/'requests'/'C01.json',request)
            manifest={'cases':{'development':[{'caseID':'C01'}],'heldOut':[{'caseID':'H01'}]}}
            calls=[]
            def fail(value):
                calls.append(value);raise OSError('redacted transport failure')
            with patch.object(c,'verify',return_value=manifest),patch.object(c,'report',return_value={}):
                for _ in range(2):
                    with self.assertRaisesRegex(ValueError,'UNCERTAIN_OUTCOME_STOP'):c.execute(root,'development',call=fail)
                self.assertEqual(len(calls),1);self.assertFalse((root/'held-out').exists())
                with self.assertRaisesRegex(ValueError,'LIVE_FLAG_REQUIRED'):c.execute(root,'held-out')

    def test_report_matched_changes_and_worksheet_preserve_baseline(self):
        """Both matched arms produce source-bound diagnostics, not gold judgments."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'calibration';original=Path(tmp)/'baseline';request=body();request['instructions']=c.p.PROMPT
            c.live.save(original/'request.json',request)
            new_request=c.variant(request);c.live.save(root/'development'/'requests'/'C01.json',new_request)
            old=recommendation();new=deepcopy(old)
            new['assessments'][0].update(recommendation='abstain',identityLevel='unresolved',missingInformation=['specificity unknown'])
            def response(value):
                return dict(id='fixture',model=c.live.MODEL,status='completed',error=None,incomplete_details=None,usage={'input_tokens':1,'output_tokens':2},
                    output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(value))])])
            c.p.attempt(original/'attempt',request,lambda _:response(old))
            c.p.attempt(root/'development'/'attempts'/'C01',new_request,lambda _:response(new))
            binding={'pairs':{'P1':'key1','P2':'key2'},'entities':{k:{'occurrenceID':'original-'+k} for k in ('E1','E2','E3')},
                     'evidence':{},'sources':{'S1':'original-source'}}
            c.live.save(root/'development'/'audit'/'C01.json',{'originalBinding':binding})
            manifest={'cases':{'development':[{'caseID':'C01','unitID':'U1','pairs':2,'tags':[],
                'baselineRequest':str(original/'request.json'),'baselineAttempt':str(original/'attempt')}],'heldOut':[]}}
            before={str(p):p.read_bytes() for p in original.rglob('*') if p.is_file()}
            with patch.object(c,'verify',return_value=manifest):report=c.report(root)
            self.assertEqual(report['stages']['development']['matchedPairs'],2)
            worksheet=c.live.load(root/'worksheet.json')['stages']['development']
            self.assertEqual(len(worksheet),2)
            self.assertEqual(sum(x['categoryChanged'] for x in worksheet),1)
            self.assertEqual(report['stages']['held-out']['matchedPairs'],0)
            self.assertEqual(before,{str(p):p.read_bytes() for p in original.rglob('*') if p.is_file()})

    def test_read_baseline_results_does_not_write_them(self):
        """Historical authenticated response comparison performs no finalization writes."""
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'baseline';request=body()
            def provider(_):
                return dict(id='fixture',model=c.live.MODEL,status='completed',error=None,incomplete_details=None,usage={'input_tokens':1,'output_tokens':2},
                    output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(recommendation()))])])
            c.p.attempt(folder,request,provider)
            before={p.name:p.read_bytes() for p in folder.iterdir()}
            outcome,value=c.result(folder,request)
            self.assertEqual(outcome['status'],'validated_recommendation_only')
            self.assertEqual(value,recommendation());self.assertEqual(before,{p.name:p.read_bytes() for p in folder.iterdir()})


if __name__=='__main__':unittest.main()
