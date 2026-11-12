"""Focused synthetic feasibility tests; no corpus execution or model calls."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import step14_automatic_acceptance_preview as p


class PreviewTests(unittest.TestCase):
    """Protect prospective state boundaries and complete-group safety."""

    def member(self, oid, cls='Tool', family='publications', artifact='one'):
        """Build a source-bound record under the current saved metadata contract."""
        return dict(occurrenceID=oid, ontologyClass=cls, inventoryId=cls,
            sourceFamilies=[family], sourceArtifacts=[artifact], versions={},
            granularity='unspecified_requires_context_review', identifierDeclarations=[],
            evidencePointers=[{'jsonPointer':'/evidenceReferences/0'}],
            originalReference={'file':'fixture'}, preparationFlags=[])

    def pair(self, a, b, category='same_entity_candidate', state='validated_recommendation'):
        """Build one explicit saved comparison with source-bound evidence IDs."""
        ids = sorted([a,b]); key=p.r.candidates.token(ids)
        return dict(pairKeySha256=key, occurrenceIDs=ids, coverageState=state,
            category=category, modelIdentityLevel='entity', ontologyClass='Tool',
            familyCombination=['publications'], identityScope='within_artifact',
            nominationOrigin='alias_extended', unitID=key,
            assessment=dict(evidenceIDs=['Q1','Q2'], conflictEvidenceIDs=[],missingInformation=[]))

    def inputs(self, ids, edges):
        """Create complete container metadata with only the supplied comparisons."""
        pairs = {x['pairKeySha256']:x for x in edges}
        bindings = {k:dict(evidence={'Q1':{'occurrenceID':v['occurrenceIDs'][0]},
                                    'Q2':{'occurrenceID':v['occurrenceIDs'][1]}}) for k,v in pairs.items()}
        members = {oid:self.member(oid) for oid in ids}
        endpoints = {oid:dict(selectedEvidence=[{'literalExcerpt':'source text'}]) for oid in ids}
        raw = dict(groupID='group', occurrenceIDs=ids, originalKey=[p.triage.queue.LEXICAL,'Tool','name'],
                   selectedPairKeys=sorted(pairs))
        group=p.combine_containers([raw])[0]
        return group,pairs,members,endpoints,bindings,raw

    def test_positive_complete_triangle_still_holds_missing_specificity(self):
        """Fluent positives and a complete clique do not certify unknown guards."""
        g,pairs,m,e,b,_=self.inputs(['a','b','c'],[self.pair('a','b'),self.pair('a','c'),self.pair('b','c')])
        before=copy.deepcopy((g,pairs,m,e,b))
        row=p.simulate(g,pairs,m,e,[],b)
        self.assertEqual(row['state'],p.HELD)
        self.assertTrue(row['safeguards']['B']['completePositiveComparisons'])
        self.assertTrue(row['safeguards']['B']['assessmentEvidenceBoundToBothEndpoints'])
        self.assertIsNone(row['safeguards']['B']['granularityCompatibility'])
        self.assertEqual((g,pairs,m,e,b),before)

    def test_missing_closing_edge_and_version_bridge_hold(self):
        """A-B-C cannot imply A-C or erase a release difference."""
        g,pairs,m,e,b,_=self.inputs(['a','b','c'],[self.pair('a','b'),self.pair('b','c')])
        m['a']['versions']={'version':'2.1'};m['c']['versions']={'version':'3.0'}
        row=p.simulate(g,pairs,m,e,[],b)
        self.assertFalse(row['safeguards']['B']['completePositiveComparisons'])
        self.assertFalse(row['safeguards']['B']['entityVersionCompatibility'])
        self.assertEqual(row['state'],p.HELD)

    def test_exact_identifier_role_and_namespace(self):
        """Own identifiers differ from local declarations, URL scopes and other keys."""
        records=[self.member(x,'DatasetResource') for x in ('a','b')]
        key=[p.triage.queue.ID,'DatasetResource','doi','10.1234/example']
        for record in records:
            record['identifierDeclarations']=[dict(scheme='doi',value=key[-1],basis='C-D04')]
        self.assertTrue(p.identifier_guard([key],records))
        records[1]['identifierDeclarations'][0]['basis']='accepted_source_local_candidate'
        self.assertFalse(p.identifier_guard([key],records))
        records[1]['identifierDeclarations'][0]['basis']='C-D04'
        self.assertFalse(p.identifier_guard([key[:-1]+['10.1234/other']],records))
        self.assertIsNone(p.identifier_guard([],records))

    def test_approval_exactness_and_negative_nonpropagation(self):
        """Pilot decisions are preserved without accepting their containing group."""
        g,pairs,m,e,b,_=self.inputs(['a','b','c'],[self.pair('a','b')])
        decisions=[dict(decisionID='pilot',occurrenceIDs=['a','b'])]
        row=p.simulate(g,pairs,m,e,decisions,b)
        self.assertEqual(row['state'],p.HELD)
        self.assertFalse(row['safeguards']['A']['pilotScopeCompatible'])
        g,pairs,m,e,b,_=self.inputs(['a','b'],[self.pair('a','b','different_entities_candidate')])
        row=p.simulate(g,pairs,m,e,decisions,b)
        self.assertEqual(row['state'],'researcher_approved_exact_scope')
        row=p.simulate(g,pairs,m,e,[],b)
        self.assertEqual(row['state'],p.NONIDENTITY)
        self.assertTrue(row['simulationOnly'])
        self.assertEqual(row['identityDecisions'],0)

    def test_class_evidence_and_prior_assessment_gates(self):
        """Prior overlaps and missing evidence cannot silently become positive evidence."""
        g,pairs,m,e,b,_=self.inputs(['a','b'],[self.pair('a','b',state='prior_group_assessment_overlap')])
        m['b']['ontologyClass']='MLModel';m['a']['evidencePointers']=[]
        row=p.simulate(g,pairs,m,e,[],{})
        for name in ('classCompatible','sourceEvidencePresent','completePositiveComparisons','assessmentEvidenceBoundToBothEndpoints'):
            self.assertFalse(row['safeguards']['B'][name])

    def test_guard_truth_table_and_overlap_barrier(self):
        """Even hypothetical eligible scopes cannot automatically form transitive unions."""
        self.assertEqual(p.guarded_state({'guard':True}),p.ACCEPTED)
        for value in (False,None):
            self.assertEqual(p.guarded_state({'guard':value}),p.HELD)
        groups=[dict(simulationID=k,occurrenceIDs=ids,state=p.ACCEPTED,holdReasons=[])
                for k,ids in [('a',['1','2']),('b',['2','3']),('c',['4','5'])]]
        p.prevent_overlaps(groups)
        self.assertEqual([x['state'] for x in groups],[p.HELD,p.HELD,p.ACCEPTED])
        self.assertEqual(groups[0]['occurrenceIDs'],['1','2'])

    def test_exact_dedup_oversized_and_nonadditive_counts(self):
        """Only identical containers deduplicate; oversized membership stays unknown."""
        g,pairs,m,e,b,raw=self.inputs(['a','b'],[self.pair('a','b')])
        other=dict(raw,groupID='other',originalKey=[p.triage.queue.ID,'Tool','literal','name'])
        oversized=[dict(originalBlock=dict(blockID='large',key=[p.triage.queue.LEXICAL,'Tool','generic'],
                    memberCount=1000000,occurrenceIDs=[],membershipSha256='saved'))]
        rows,prs,summary=p.evaluate([raw,other],pairs,m,e,[],oversized,b)
        self.assertEqual(summary['candidateCompleteScopes'],1)
        self.assertEqual(summary['oversizedScopes'],1)
        self.assertEqual(rows[-1]['occurrenceIDs'],[])
        self.assertEqual(len(prs),1)
        self.assertFalse(summary['automaticEvaluationFrameExists'])
        self.assertEqual(summary['evaluationCasesDrawn'],0)
        self.assertEqual(p.evaluate([other,raw],pairs,m,e,[],oversized,b),(rows,prs,summary))

    def test_synthetic_artifact_run_and_hash_guard(self):
        """Verify saved-input integration, repeatability and failure before publication."""
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);source=base/'triage';source.mkdir()

            def write(path,value,lines=False):
                """Write synthetic canonical fixtures."""
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b''.join(p.r.identity.encoded(x)+b'\n' for x in value) if lines
                                 else p.r.identity.encoded(value)+b'\n')

            g,pairs,m,e,b,raw=self.inputs(['a','b'],[self.pair('a','b')])
            for oid in e:e[oid]['occurrenceID']=oid
            for uid in b:b[uid]['unitID']=uid
            mp=base/'referent-groups/v1/members.jsonl';ep=base/'unified-review-queue/v1/endpoint-provenance.jsonl'
            bp=base/'unified-review-queue/v1/unit-bindings.jsonl';ledger=base/'ledger.jsonl';doc=base/'doc.json'
            for path,value in [(mp,list(m.values())),(ep,list(e.values())),(bp,list(b.values())),(ledger,[])]:
                write(path,value,True)
            write(doc,{})
            authority=base/'semantic-candidates/v1/manifest.json'
            write(authority,dict(inputHashes={name:p.r.identity.sha(Path(name)) for name in
                ('src/ontology/ontology_spec.yaml','src/ontology/ciroh_ontology.owl')}))
            original=dict(pairCoverageStates={'validated_recommendation':1},selectedPoolPairs=1,
                          validatedRecommendationPairs=1,generationOrigins={'batch':1},preservedNextQueueCoverage={},
                          oversizedCrossFamilyBlocks=0,discoveryRouteCoverage=[])
            write(source/'summary.json',original)
            for name,value in [('pair-inventory.jsonl',list(pairs.values())),('review-groups.jsonl',[raw]),
                               ('block-coverage.jsonl',[]),('prior-decisions.jsonl',[]),('oversized-inventory.jsonl',[])]:
                write(source/name,value,True)
            write(source/'manifest.json',dict(version='step14-adjudication-triage/0.1.0',
                  inputHashes={str(x):p.r.identity.sha(x) for x in (mp,ep,bp,ledger,doc,authority)},
                  outputHashes={x.name:p.r.identity.sha(x) for x in source.iterdir()}))
            with patch.object(p.triage,'BASE',base),patch.object(p,'ROOT',base/'out'), \
                 patch.object(p.triage.queue.approvals,'APPROVALS',ledger), \
                 patch.object(p.triage.queue.approvals,'DOCUMENT',doc), \
                 patch.object(p.triage.queue.approvals,'validate_approvals'), \
                 patch.object(p.socket.socket,'connect',side_effect=AssertionError('network forbidden')):
                result=p.run(source,base/'out/first')
                self.assertEqual(result['provisionalAcceptedGroups'],0)
                self.assertEqual(p.run(source,base/'out/second'),result)
                for path in (base/'out/first').iterdir():
                    self.assertEqual(path.read_bytes(),(base/'out/second'/path.name).read_bytes())
                with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT_REQUIRED'):
                    p.run(source,base/'out/first')
                ep.write_text('{}\n')
                with self.assertRaises(ValueError):p.run(source,base/'out/bad')
                self.assertFalse((base/'out/bad').exists())


if __name__=='__main__':
    unittest.main()
