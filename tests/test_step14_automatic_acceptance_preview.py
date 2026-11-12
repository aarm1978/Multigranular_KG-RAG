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
            assessment=dict(evidenceIDs=['E1Q1','E2Q1'], conflictEvidenceIDs=[],missingInformation=[],
                granularityAssessment='Same named tool at project granularity.',
                versionAssessment='No entity release conflict is established.',
                ownerReferenceAssessment='Both evidence excerpts concern the tool itself.'))

    def inputs(self, ids, edges):
        """Create complete container metadata with only the supplied comparisons."""
        pairs = {x['pairKeySha256']:x for x in edges}
        bindings = {k:dict(
            entities={f'E{i+1}':dict(occurrenceID=oid,endpointRecordSha256='saved')
                      for i,oid in enumerate(v['occurrenceIDs'])},
            evidence={f'E{i+1}Q1':dict(occurrenceID=oid,selectedFragmentIndex=0,
                      usedStart=0,usedEnd=20,shortened=False)
                      for i,oid in enumerate(v['occurrenceIDs'])}) for k,v in pairs.items()}
        members = {oid:self.member(oid) for oid in ids}
        endpoints = {oid:dict(selectedEvidence=[{'literalExcerpt':'source text'}]) for oid in ids}
        raw = dict(groupID='group', occurrenceIDs=ids, originalKey=[p.triage.queue.LEXICAL,'Tool','name'],
                   selectedPairKeys=sorted(pairs))
        group=p.combine_containers([raw])[0]
        return group,pairs,members,endpoints,bindings,raw

    def test_positive_complete_triangle_accepts_predicted_identity(self):
        """Complete supported predictions pass without a semantic-truth certificate."""
        g,pairs,m,e,b,_=self.inputs(['a','b','c'],[self.pair('a','b'),self.pair('a','c'),self.pair('b','c')])
        before=copy.deepcopy((g,pairs,m,e,b))
        row=p.simulate(g,pairs,m,e,[],b)
        self.assertEqual(row['state'],p.ACCEPTED)
        self.assertEqual(row['acceptedBy'],['B'])
        self.assertTrue(row['safeguards']['B']['completePositiveComparisons'])
        self.assertTrue(row['safeguards']['B']['assessmentEvidenceBoundToBothEndpoints'])
        self.assertIn('structured_granularity_unspecified_prediction_not_verification',row['evidenceInterpretation']['limitations'])
        self.assertEqual((g,pairs,m,e,b),before)

    def test_missing_closing_edge_and_version_bridge_hold(self):
        """A-B-C cannot imply A-C or erase a release difference."""
        g,pairs,m,e,b,_=self.inputs(['a','b','c'],[self.pair('a','b'),self.pair('b','c')])
        m['a']['versions']={'version':'2.1'};m['c']['versions']={'version':'3.0'}
        row=p.simulate(g,pairs,m,e,[],b)
        self.assertFalse(row['safeguards']['B']['completePositiveComparisons'])
        self.assertTrue(row['safeguards']['B']['noDemonstratedConflict'])
        self.assertIn('raw_version_metadata_differs_role_not_inferred',row['evidenceInterpretation']['limitations'])
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
        self.assertTrue(summary['automaticEvaluationFrameExists'])
        self.assertEqual(summary['acceptedByRoute']['B']['groups'],1)
        self.assertEqual(summary['evaluationCasesDrawn'],0)
        self.assertEqual(p.evaluate([other,raw],pairs,m,e,[],oversized,b),(rows,prs,summary))

    def test_two_member_llm_acceptance_and_capture_metadata(self):
        """Unequal raw capture metadata does not become scientific incompatibility."""
        g,pairs,m,e,b,_=self.inputs(['a','b'],[self.pair('a','b')])
        m['a']['versions']={'commitSHA':'capture-a','cffVersion':'1.1'}
        m['b']['versions']={'commitSHA':'capture-b','cffVersion':'1.2'}
        before=copy.deepcopy((g,pairs,m,e,b))
        row=p.simulate(g,pairs,m,e,[],b)
        self.assertEqual(row['state'],p.ACCEPTED)
        self.assertEqual(row['acceptedBy'],['B'])
        self.assertEqual((g,pairs,m,e,b),before)
        self.assertEqual(row['identityDecisions'],0)

    def test_owned_identifier_group_accepts_without_llm_pairs(self):
        """A complete exact own-key scope has its separate predicted acceptance route."""
        g,pairs,m,e,b,_=self.inputs(['a','b'],[])
        g['originalKeys']=[[p.triage.queue.ID,'DatasetResource','doi','10.1234/example']]
        for member in m.values():
            member.update(ontologyClass='DatasetResource',inventoryId='DatasetResource',
                identifierDeclarations=[dict(scheme='doi',value='10.1234/example',basis='C-D04')])
        row=p.simulate(g,pairs,m,e,[],b)
        self.assertEqual(row['state'],p.ACCEPTED)
        self.assertEqual(row['acceptedBy'],['A'])
        self.assertEqual(row['missingExplicitComparisons'],1)
        m['b']['identifierDeclarations'].append(dict(scheme='hydroshare',value='other',basis='deterministic_entity_own_field'))
        m['a']['identifierDeclarations'].append(dict(scheme='hydroshare',value='one',basis='deterministic_entity_own_field'))
        row=p.simulate(g,pairs,m,e,[],b)
        self.assertEqual(row['state'],p.HELD)
        self.assertIn('demonstrated_incompatibility',row['holdKinds'])

    def test_explicit_version_referent_and_missing_information_blocks(self):
        """Saved conflict evidence blocks even a positive prediction; ambiguity is separate."""
        for explanation in ('Entity releases v2.1 and v3.0 conflict.',
                            'The referents are a base dataset and a derived product.'):
            g,pairs,m,e,b,_=self.inputs(['a','b'],[self.pair('a','b')])
            assessment=next(iter(pairs.values()))['assessment']
            assessment.update(conflictEvidenceIDs=['E1Q1','E2Q1'],versionAssessment=explanation)
            row=p.simulate(g,pairs,m,e,[],b)
            self.assertEqual(row['state'],p.HELD)
            self.assertIn('demonstrated_incompatibility',row['holdKinds'])
        assessment['conflictEvidenceIDs']=[]
        assessment['missingInformation']=['Unknown referent scope.']
        row=p.simulate(g,pairs,m,e,[],b)
        self.assertEqual(row['state'],p.HELD)
        self.assertIn('missing_evidence_or_unresolved_ambiguity',row['holdKinds'])
        self.assertNotIn('demonstrated_incompatibility',row['holdKinds'])
        assessment['missingInformation']=[]
        m['a']['granularity']='named dataset resource';m['b']['granularity']='derived product'
        self.assertEqual(p.simulate(g,pairs,m,e,[],b)['state'],p.HELD)

    def test_real_positive_scopes_are_blocked_by_overlap(self):
        """Two individually acceptable model pairs cannot become an automatic chain."""
        g,pairs,m,e,b,_=self.inputs(['a','b','c'],[self.pair('a','b'),self.pair('b','c')])
        groups=[dict(groupID=k,occurrenceIDs=v['occurrenceIDs'],selectedPairKeys=[k]) for k,v in pairs.items()]
        rows,prs,summary=p.evaluate(groups,pairs,m,e,[],[],b)
        self.assertEqual(summary['preOverlapAcceptedGroups'],2)
        self.assertEqual(summary['overlapBlockedGroups'],2)
        self.assertEqual(summary['provisionalAcceptedGroups'],0)
        self.assertEqual(len(prs),2)
        self.assertTrue(all(row['state']==p.HELD for row in rows))

    def test_quote_relation_and_mixed_citations_accept_without_mutation(self):
        """Authentic Q/R sidecar shapes resolve through the local entity alias."""
        for citations in (['E1Q1','E2Q1'], ['E1R1','E2R1'], ['E1Q1','E2R1'],
                          ['E1R1','E2Q1'], ['E1Q1','E1R1','E2R1']):
            with self.subTest(citations=citations):
                g,pairs,m,e,b,_=self.inputs(['a','b'],[self.pair('a','b')])
                pair=next(iter(pairs.values()));binding=b[pair['unitID']]
                for alias in ('E1','E2'):
                    binding['evidence'][alias+'R1']=dict(
                        file='saved/accepted-relation-context.jsonl',line=7,recordSha256='saved-relation')
                pair['assessment']['evidenceIDs']=citations
                before=copy.deepcopy((pairs,b))
                result=p.simulate(g,pairs,m,e,[],b)
                self.assertTrue(result['safeguards']['B']['assessmentEvidenceBoundToBothEndpoints'])
                self.assertEqual(result['state'],p.ACCEPTED)
                self.assertEqual(result['identityDecisions'],0)
                self.assertEqual((pairs,b),before)

    def test_malformed_or_incomplete_citations_fail_closed(self):
        """Malformed IDs cannot borrow a plausible reference or cover missing endpoints."""
        g,pairs,m,e,b,_=self.inputs(['a','b'],[self.pair('a','b')])
        binding=next(iter(b.values()))
        for bad in ('Q1','E1','E0Q1','E01Q1','E1Q0','E1R01','E1X1','E1Q1extra','E1Q1\n','E1Q1R1'):
            with self.subTest(evidenceID=bad):
                trial=copy.deepcopy(binding)
                trial['evidence'][bad]=trial['evidence']['E1Q1']
                self.assertFalse(p.evidence_covers_endpoints([bad,'E2Q1'],trial,['a','b']))
        for cited in ([],None,'E1Q1',['E1Q1'],['E1Q1','E1Q1'],['E1Q99','E2Q1'],[{},'E2Q1']):
            with self.subTest(cited=cited):
                self.assertFalse(p.evidence_covers_endpoints(cited,binding,['a','b']))

    def test_missing_alias_wrong_endpoint_and_inconsistent_quote_hold(self):
        """Every citation must bind to this comparison, even if both endpoints are cited."""
        for defect in ('missing_alias','missing_entity_id','wrong_endpoint','inconsistent_quote',
                       'missing_quote_id','empty_relation','extra_wrong_endpoint'):
            with self.subTest(defect=defect):
                g,pairs,m,e,b,_=self.inputs(['a','b'],[self.pair('a','b')])
                pair=next(iter(pairs.values()));binding=b[pair['unitID']]
                if defect=='missing_alias':del binding['entities']['E1']
                elif defect=='missing_entity_id':del binding['entities']['E1']['occurrenceID']
                elif defect=='wrong_endpoint':binding['entities']['E1']['occurrenceID']='outside'
                elif defect=='inconsistent_quote':binding['evidence']['E1Q1']['occurrenceID']='b'
                elif defect=='missing_quote_id':del binding['evidence']['E1Q1']['occurrenceID']
                elif defect=='empty_relation':
                    binding['evidence']['E1R1']={}
                    pair['assessment']['evidenceIDs']=['E1R1','E2Q1']
                else:
                    binding['entities']['E3']={'occurrenceID':'outside'}
                    binding['evidence']['E3R1']={'file':'saved/relations.jsonl','line':3,'recordSha256':'saved'}
                    pair['assessment']['evidenceIDs'].append('E3R1')
                result=p.simulate(g,pairs,m,e,[],b)
                self.assertFalse(result['safeguards']['B']['assessmentEvidenceBoundToBothEndpoints'])
                self.assertEqual(result['state'],p.HELD)

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
                self.assertEqual(result['provisionalAcceptedGroups'],1)
                self.assertEqual(result['identityDecisions'],0)
                self.assertEqual(result['graphWrites'],0)
                self.assertEqual(ledger.read_bytes(),b'')
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
