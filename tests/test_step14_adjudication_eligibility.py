"""Focused offline eligibility tests; recommendations never become approvals."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import step14_adjudication_eligibility as e
from test_step14_evidence_review_batch import named, pair as original_pair
from test_step14_retrieval_reconciliation import nomination


def pair(a,b):
    """High joint reciprocal fixture; selection signal, never identity."""
    p=original_pair(a,b);scores=dict(name=.9,evidence=.85)
    p["directions"]=[dict(nomination=nomination(a,b,scores=scores)),dict(nomination=nomination(b,a,scores=scores))]
    return p


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
        self.assertTrue(result['previousUnresolved']);self.assertTrue(result['eligible']['alias_extended'])
        self.assertEqual(result['approvedSubsetIDs'],[])

    def test_existing_unadjudicated_batch_is_not_new_or_approved(self):
        """A queued pair remains eligible but is not counted as newly discovered."""
        a=named('a','RiverEngine');b=named('b','OtherEngine');p=pair(a,b)
        result=e.assess(p,{'a':a,'b':b},{p['pairKeySha256']:{'caseID':'R01','occurrenceIDs':['a','b']}})
        self.assertTrue(result['eligible']['alias_extended'])
        self.assertTrue(result['previousUnresolved'])
        self.assertFalse(result['newRelativeToAuthorities'])
        self.assertEqual(result['approvedSubsetIDs'],[])

    def test_name_only_evidence_only_and_both_paths(self):
        """Neither an exact name match nor two high scores is necessary."""
        a=named('a','RiverEngine');b=named('b','Routing package',quote='Provides channel routing through a documented hydrological solver.')
        b['selectedEvidence'][0]['labelPresent']=False
        rows={'a':a,'b':b}
        for views,scores in [(['name'],{'name':.95,'evidence':.1}),(['evidence'],{'name':.1,'evidence':.95}),(['name','evidence'],{'name':.6,'evidence':.6})]:
            p=pair(a,b);p['nominationViews']=views;
            for d in p['directions']:d['nomination']['scores']=scores
            result=e.assess(p,rows)
            self.assertEqual(result['eligible']['alias_extended'],max(scores.values())>=.95)
            self.assertEqual(result['scores'],scores)

    def test_unknown_versions_generic_names_not_automatic_decisions(self):
        """Ambiguity flags preserve plausible candidates and all original records."""
        a=named('a','model');b=named('b','model');b['versions']={'version':'2'}
        rows={'a':a,'b':b};p=pair(a,b);before=deepcopy((rows,p))
        result=e.assess(p,rows)
        self.assertTrue(result['eligible']['alias_extended'])
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
        self.assertFalse(result['eligible']['dual']);self.assertFalse(result['eligible']['alias_extended'])
        self.assertEqual(result['reasons']['alias_extended'],'insufficient_identity_context')
        a['selectedEvidence']=[]
        result=e.assess(p,rows);self.assertEqual(result['reasons']['dual'],'missing_literal_or_provenance')
        self.assertEqual(p,before)

    def test_overlapping_groups_no_union_or_leaf_pairs(self):
        """Direct groups are packaging references only."""
        groups={'ab':{'occurrenceIDs':['a','b']},'bc':{'occurrenceIDs':['b','c']}}
        index={'a':{'ab'},'b':{'ab','bc'},'c':{'bc'}}
        self.assertEqual(e.unit_key(['a','b'],index,groups),'direct:ab')
        self.assertEqual(e.unit_key(['a','c'],index,groups),'center:a')
        self.assertEqual(e.unit_key(['b','c'],index,groups),'direct:bc')

    def test_units_preserve_exact_pairs_and_actual_context_workload(self):
        """Referent contexts create unlimited units without adding pair identities."""
        endpoints={str(i):named(str(i),'RiverEngine') for i in range(11)}
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);db=sqlite3.connect(':memory:')
            db.execute('CREATE TABLE pairs(pairkey TEXT, container TEXT, dual INT, alias_extended INT, ambiguity_extended INT, detail TEXT)')
            for i in range(1,11):
                p={'pairKeySha256':str(i),'occurrenceIDs':['0',str(i)]}
                db.execute('INSERT INTO pairs VALUES(?,?,1,1,0,?)',(str(i),'center:0',json.dumps(p)))
            db.execute('INSERT INTO pairs VALUES(?,?,0,0,0,?)',('nonselected','center:0',json.dumps({'pairKeySha256':'nonselected','occurrenceIDs':['1','2']})))
            before=db.execute('SELECT * FROM pairs ORDER BY pairkey').fetchall()
            stats=e.emit_units(db,root,endpoints,{})
            self.assertEqual(db.execute('SELECT * FROM pairs ORDER BY pairkey').fetchall(),before)
            self.assertEqual(stats['dual']['eligiblePairs'],10)
            self.assertGreater(stats['dual']['proposedReviewUnits'],0)
            self.assertLessEqual(stats['dual']['proposedReviewUnits'],10)
            self.assertEqual(stats['ambiguity_extended']['proposedReviewUnits'],0)
            rows=list(e.r.rows(root/'review-units.jsonl'))
            contexts={x['contextID']:x['payload'] for x in e.r.rows(root/'llm-contexts.jsonl')}
            sidecars={x['unitID']:x for x in e.r.rows(root/'unit-sidecars.jsonl')}
            for unit in rows:
                payload=contexts[unit['contextID']]
                self.assertEqual(unit['contextID'],e.r.candidates.token(payload))
                self.assertEqual(unit['contextUTF8Bytes'],len(e.r.identity.encoded(payload)))
                self.assertLessEqual(len(payload['entities']),12)
                self.assertEqual(len(sidecars[unit['unitID']]['pairs']),unit['pairCount'])
            self.assertEqual(sum(x['pairCount'] for x in rows if x['policy']=='dual'),10)
            db.close()

    def test_compact_context_excludes_administrative_and_score_fields(self):
        """Only whitelisted scientific content reaches a prospective LLM."""
        a=named('a','RiverEngine');b=named('b','OtherEngine')
        a['versions']={'version':'2','cffVersion':'administrative'}
        p=pair(a,b);p['assessment']={'scores':{'name':.99},'previousModelRecommendation':'secret'}
        payload,sidecar=e.compact_context([p],{'a':a,'b':b})
        text=json.dumps(payload)
        for forbidden in ('Sha256','originalReference','jsonPointer','previousModelRecommendation','priorMemberships','scores','cffVersion'):
            self.assertNotIn(forbidden,text)
        self.assertEqual(payload['entities'][0]['id'],'E1')
        self.assertEqual(payload['entities'][0]['recordedVersionOrImplementation'],{'version':'2'})
        self.assertEqual(sidecar['pairs']['P1'],p)
        self.assertEqual(sidecar['entities']['E1'],a)

    def test_moderate_similarity_no_longer_qualifies_from_prose_alone(self):
        """Substantial context and reciprocity cannot replace score/cue selection."""
        a=named('a','ARLSTM');b=named('b','LSTM');p=pair(a,b)
        for d in p['directions']:d['nomination']['scores']=dict(name=.862,evidence=.545)
        result=e.assess(p,{'a':a,'b':b})
        self.assertFalse(any(result['eligible'].values()))
        self.assertEqual(result['reasons']['alias_extended'],'score_or_corroboration_not_selected_unresolved')

    def test_targeted_ambiguity_route_and_boundary(self):
        """Explicit specificity questions have a distinct, corroborated pathway."""
        a=named('a','RiverEngine');b=named('b','RiverEngine');b['versions']={'version':'2'}
        p=pair(a,b)
        for d in p['directions']:d['nomination']['scores']=dict(name=.90,evidence=.70)
        result=e.assess(p,{'a':a,'b':b},frequencies=Counter(riverengine=1))
        self.assertFalse(result['eligible']['alias_extended'])
        self.assertTrue(result['eligible']['ambiguity_extended'])
        for d in p['directions']:d['nomination']['scores']['evidence']=.649
        self.assertFalse(any(e.assess(p,{'a':a,'b':b},frequencies=Counter(riverengine=1))['eligible'].values()))

    def test_incident_roles_and_exact_literal_substrings(self):
        """Only literal relationship context is exposed; its authority stays local."""
        a=named('a','RiverEngine',quote='RiverEngine '+('documented context '*40))
        a['incidentContext']=[dict(modelFields=dict(direction='incoming',predicate='usesTool',
            otherClass='Repository',otherNames=['Example'],literalEvidence=['uses RiverEngine']),
            originalReference=dict(file='private/path',recordSha256='hash'))]
        payload,sidecar=e.compact_context([dict(pairKeySha256='x',occurrenceIDs=['a'])],{'a':a})
        quote=payload['entities'][0]['evidence'][0]['text']
        self.assertEqual(quote,a['selectedEvidence'][0]['literalExcerpt'][:420])
        self.assertTrue(sidecar['evidence']['E1Q1']['shortened'])
        self.assertEqual(payload['entities'][0]['incidentRelations'][0]['predicate'],'usesTool')
        self.assertNotIn('private/path',json.dumps(payload))
        self.assertIn('private/path',json.dumps(sidecar))

    def test_refuse_existing_output(self):
        """A failed or completed output is never overwritten."""
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with patch.object(e,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT_REQUIRED'):e.run(root)


if __name__=='__main__':unittest.main()
