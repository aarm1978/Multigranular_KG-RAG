"""Offline queue coverage, provenance and nontransitivity checks."""
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from src.evaluation import step14_unified_review_queue as q
from test_step14_evidence_review_batch import named


class QueueTests(unittest.TestCase):
    def setUp(self):
        """No network access in fixtures."""
        for method in ('connect','connect_ex'):
            p=patch.object(socket.socket,method,side_effect=AssertionError('OFFLINE'));p.start();self.addCleanup(p.stop)

    def test_exact_approval_and_prior_assessment_distinctions(self):
        """Approvals never extend transitively; prior larger groups are not pair decisions."""
        rows={x:named(x,'RiverEngine') for x in 'abc'}
        rows['a']['priorMemberships']['approved']=['ab'];rows['b']['priorMemberships']['approved']=['ab','bc'];rows['c']['priorMemberships']['approved']=['bc']
        pair=lambda ids:dict(occurrenceIDs=ids,pairKeySha256=q.r.candidates.token(ids))
        self.assertEqual(q.disposition(pair(['a','b']),rows,{}),'approved_excluded')
        ac=pair(['a','c']);self.assertEqual(q.disposition(ac,rows,{}),'queued')
        prior={ac['pairKeySha256']:[dict(disposition='prior_group_assessment_overlap')]}
        self.assertEqual(q.disposition(ac,rows,prior),'prior_group_assessment_overlap')
        prior[ac['pairKeySha256']].append(dict(disposition='prior_completed_pair_assessment'))
        self.assertEqual(q.disposition(ac,rows,prior),'prior_completed_pair_assessment')

    def test_complete_bounded_pair_coverage_and_context_privacy(self):
        """Splitting covers explicit pairs once without adding leaf-to-leaf judgments."""
        ends={str(i):named(str(i),'NWM',family='github' if i%2 else 'publications') for i in range(17)}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);db=sqlite3.connect(':memory:')
            db.execute('CREATE TABLE candidates(pairkey TEXT PRIMARY KEY,container TEXT,detail TEXT,disposition TEXT,origin TEXT,unit TEXT)')
            for i in range(1,17):
                ids=sorted(['0',str(i)]);p=dict(pairKeySha256=q.r.candidates.token(ids),occurrenceIDs=ids,originalReference={'file':'private/path'},scores={'name':.99})
                db.execute('INSERT INTO candidates VALUES(?,?,?,"queued","fixture",NULL)',(p['pairKeySha256'],'anchor',json.dumps(p)))
            db.execute('INSERT INTO candidates VALUES("deferred","other","{}","prior_group_assessment_overlap","fixture",NULL)')
            result=q.emit(db,root,ends)
            self.assertEqual(result['queuedPairs'],16);self.assertGreater(result['reviewUnits'],1)
            self.assertEqual(db.execute('SELECT count(*) FROM candidates WHERE unit IS NOT NULL').fetchone()[0],16)
            contexts=list(q.r.rows(root/'contexts.jsonl'));bindings=list(q.r.rows(root/'unit-bindings.jsonl'))
            self.assertEqual(sum(len(c['payload']['pairs']) for c in contexts),16)
            for c,b in zip(contexts,bindings):
                self.assertEqual(b['contextSha256'],q.r.candidates.token(c['payload']))
                self.assertLessEqual(len(c['payload']['pairs']),12)
                self.assertLessEqual(len(c['payload']['entities']),12)
                self.assertLessEqual(len(q.r.identity.encoded(c['payload'])),12000)
                for forbidden in ('private/path','scores','Sha256','priorMemberships'):
                    self.assertNotIn(forbidden,json.dumps(c['payload']))
                for ref in b['entities'].values():self.assertEqual(ref['endpointRecordSha256'],q.r.candidates.token(ends[ref['occurrenceID']]))
            self.assertEqual(db.execute('SELECT unit FROM candidates WHERE pairkey="deferred"').fetchone()[0],None)
            db.close()

    def test_no_transitive_container_union_and_version_partition(self):
        """Shared-key presentation does not create a connected-component identity."""
        rows={x:named(x,'RiverEngine') for x in 'abc'}
        groups={'ab':{'occurrenceIDs':['a','b']},'bc':{'occurrenceIDs':['b','c']}}
        index={'a':{'ab'},'b':{'ab','bc'},'c':{'bc'}}
        p=dict(occurrenceIDs=['a','c'])
        self.assertTrue(q.container(p,rows,index,groups).startswith('center:a:'))
        before=q.container(p,rows,index,groups);rows['c']['versions']={'version':'3'}
        self.assertNotEqual(q.container(p,rows,index,groups),before)

    def test_prior_assessment_exact_alias_binding_without_transitive_pairs(self):
        """Read hash-bound original model scopes; A-B and B-C do not assess A-C."""
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);refs={}
            values={'audit':{'aliases':{'O1':'a','O2':'b','O3':'c'}},
                    'originalModelRecommendation':{'modelAuthored':{'assessments':[{'occurrenceIDs':['O1','O2']},{'occurrenceIDs':['O2','O3']}]}},
                    'terminal':{'status':'validated_recommendation_only'}}
            for field,value in values.items():
                path=root/(field+'.json');q.r.write(path,value)
                refs[field]={'file':str(path),'sha256':q.r.identity.sha(path)}
            case=dict(refs,caseAlias='C1',occurrences=[{'alias':'O1','occurrenceID':'a'},{'alias':'O2','occurrenceID':'b'},{'alias':'O3','occurrenceID':'c'}])
            result=q.prior_assessments({'cases':[case]}, {})
            self.assertIn(q.r.candidates.token(['a','b']),result)
            self.assertNotIn(q.r.candidates.token(['a','c']),result)
            refs['audit']['sha256']='corrupt'
            with self.assertRaises(ValueError):q.prior_assessments({'cases':[case]}, {})

    def test_existing_output_refused(self):
        """Never overwrite partial or completed queue artifacts."""
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(q,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT_REQUIRED'):q.run(root)


if __name__=='__main__':unittest.main()
