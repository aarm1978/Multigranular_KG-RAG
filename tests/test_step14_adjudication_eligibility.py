"""Focused offline eligibility tests; recommendations never become approvals."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import step14_adjudication_eligibility as e
from test_step14_evidence_review_batch import named, pair


class EligibilityTests(unittest.TestCase):
    def setUp(self):
        """Prevent provider/network activity in every fixture."""
        for method in ('connect','connect_ex'):
            p=patch.object(socket.socket,method,side_effect=AssertionError('OFFLINE'))
            p.start();self.addCleanup(p.stop)

    def test_exact_approval_not_transitive_or_co_review(self):
        """Only one exact approved subset excludes a pair."""
        a,b,c=[named(x,'RiverEngine') for x in 'abc']
        a['priorMemberships']['approved']=['ab'];b['priorMemberships']['approved']=['ab','bc'];c['priorMemberships']['approved']=['bc']
        rows={x['occurrenceID']:x for x in (a,b,c)}
        self.assertFalse(any(e.assess(pair(a,b),rows)['eligible'].values()))
        a['priorMemberships']['reviewed']=c['priorMemberships']['reviewed']=['case']
        result=e.assess(pair(a,c),rows)
        self.assertTrue(result['previousUnresolved']);self.assertTrue(result['eligible']['context_either'])
        self.assertEqual(result['approvedSubsetIDs'],[])

    def test_existing_unadjudicated_batch_is_not_new_or_approved(self):
        """A queued pair remains eligible but is not counted as newly discovered."""
        a=named('a','RiverEngine');b=named('b','OtherEngine');p=pair(a,b)
        result=e.assess(p,{'a':a,'b':b},{p['pairKeySha256']:{'caseID':'R01','occurrenceIDs':['a','b']}})
        self.assertTrue(result['eligible']['context_either'])
        self.assertTrue(result['previousUnresolved'])
        self.assertFalse(result['newRelativeToAuthorities'])
        self.assertEqual(result['approvedSubsetIDs'],[])

    def test_name_only_evidence_only_and_both_paths(self):
        """Neither an exact name match nor two high scores is necessary."""
        a=named('a','RiverEngine');b=named('b','Routing package',quote='Provides channel routing through a documented hydrological solver.')
        b['selectedEvidence'][0]['labelPresent']=False
        rows={'a':a,'b':b}
        for views,scores in [(['name'],{'name':.95,'evidence':.1}),(['evidence'],{'name':.1,'evidence':.95}),(['name','evidence'],{'name':.6,'evidence':.6})]:
            p=pair(a,b);p['nominationViews']=views;p['directions'][0]['nomination']['scores']=scores
            result=e.assess(p,rows)
            self.assertTrue(result['eligible']['context_either'])
            self.assertEqual(result['scores'],scores)

    def test_unknown_versions_generic_names_not_automatic_decisions(self):
        """Ambiguity flags preserve plausible candidates and all original records."""
        a=named('a','model');b=named('b','model');b['versions']={'version':'2'}
        rows={'a':a,'b':b};p=pair(a,b);before=deepcopy((rows,p))
        result=e.assess(p,rows)
        self.assertTrue(result['eligible']['context_either'])
        self.assertIn('generic_name_collision_risk',result['flags'])
        self.assertIn('version_metadata_differs_or_missing',result['flags'])
        self.assertEqual((rows,p),before)
        b['ontologyClass']='Algorithm'
        with self.assertRaisesRegex(ValueError,'CLASS_BINDING_DRIFT'):e.assess(p,rows)

    def test_nonselection_is_preserved_with_explicit_reason(self):
        """Thin context remains eligible under the broad alternative, never rejected."""
        a=named('a','RiverEngine',quote='RiverEngine');b=named('b','OtherEngine',quote='OtherEngine')
        rows={'a':a,'b':b};p=pair(a,b);before=deepcopy(p)
        result=e.assess(p,rows)
        self.assertTrue(result['eligible']['literal']);self.assertFalse(result['eligible']['context_either'])
        self.assertEqual(result['reasons']['context_either'],'thin_context_deferred_not_rejected')
        a['selectedEvidence']=[]
        result=e.assess(p,rows);self.assertEqual(result['reasons']['literal'],'missing_literal_or_provenance')
        self.assertEqual(p,before)

    def test_overlapping_groups_no_union_or_leaf_pairs(self):
        """Direct groups are packaging references only."""
        groups={'ab':{'occurrenceIDs':['a','b']},'bc':{'occurrenceIDs':['b','c']}}
        index={'a':{'ab'},'b':{'ab','bc'},'c':{'bc'}}
        self.assertEqual(e.unit_key(['a','b'],index,groups),'direct:ab')
        self.assertEqual(e.unit_key(['a','c'],index,groups),'center:a')
        self.assertEqual(e.unit_key(['b','c'],index,groups),'direct:bc')

    def test_units_preserve_exact_pairs_and_actual_context_workload(self):
        """Eight-pair contexts create unlimited units without adding pair identities."""
        endpoints={str(i):named(str(i),'RiverEngine') for i in range(11)}
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);db=sqlite3.connect(':memory:')
            db.execute('CREATE TABLE pairs(pairkey TEXT, container TEXT, literal INT, context_either INT, context_both INT, detail TEXT)')
            for i in range(1,11):
                p={'pairKeySha256':str(i),'occurrenceIDs':['0',str(i)]}
                db.execute('INSERT INTO pairs VALUES(?,?,1,1,0,?)',(str(i),'center:0',json.dumps(p)))
            db.execute('INSERT INTO pairs VALUES(?,?,0,0,0,?)',('nonselected','center:0',json.dumps({'pairKeySha256':'nonselected','occurrenceIDs':['1','2']})))
            before=db.execute('SELECT * FROM pairs ORDER BY pairkey').fetchall()
            stats=e.emit_units(db,root,endpoints,{})
            self.assertEqual(db.execute('SELECT * FROM pairs ORDER BY pairkey').fetchall(),before)
            self.assertEqual(stats['literal']['eligiblePairs'],10)
            self.assertEqual(stats['literal']['proposedReviewUnits'],2)
            self.assertEqual(stats['context_both']['proposedReviewUnits'],0)
            rows=list(e.r.rows(root/'review-units.jsonl'))
            for unit in rows:
                payload=e.context_payload(unit['pairs'],endpoints,{})
                self.assertEqual(unit['contextSha256'],e.r.candidates.token(payload))
                self.assertEqual(unit['contextUTF8Bytes'],len(e.r.identity.encoded(payload)))
            self.assertEqual(sum(len(x['pairs']) for x in rows if x['policy']=='literal'),10)
            db.close()

    def test_refuse_existing_output(self):
        """A failed or completed output is never overwritten."""
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with patch.object(e,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT_REQUIRED'):e.run(root)


if __name__=='__main__':unittest.main()
