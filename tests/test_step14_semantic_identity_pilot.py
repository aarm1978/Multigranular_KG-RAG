"""Synthetic bounded packaging and recommendation tests; no corpus or API execution."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from src.evaluation import step14_semantic_identity_pilot as m
from src.evaluation import step14_shared_references as shared
from tests.test_step14_alignment_opportunities import node, edge, SPEC


def occurrence(n: dict) -> dict:
    """Create a prepared occurrence preserving its original node and documentary evidence."""
    return dict(occurrenceID=n['id'],ontologyClass=n['class'],inventoryId=n['inventoryId'],
        attributes=deepcopy(n['attributes']),versions={},labels=[n['attributes'].get('name','Example')],
        contextualDescriptions=[],identifierDeclarations=[],declaredExistingNodeIDs=[],originalCandidates=[],nativeReferences=[],
        sourceFamilies=['publications'],sourceArtifacts=[n.get('evidence',{}).get('sourceArtifact','paper:unknown')],
        evidenceReferences=[deepcopy(n['evidence'])] if n.get('evidence') else [],preparationFlags=[],
        originalSnapshotRecord=deepcopy(n),snapshotRecordSha256=m.candidates.token(n))


def hub(members=('a','b'), tier='A') -> dict:
    """Represent an existing saved cross-family hub; not an adjudicated identity."""
    return dict(connectionScope='cross_family',evidenceTier=tier,targetIDs=list(members),targetClass='Paper',
        identityScope='entity_own_record' if tier=='A' else 'literal_locator',identifierScheme='doi' if tier=='A' else 'literal_locator',
        identifierValue='10.1234/example' if tier=='A' else 'https://example.org',sourceFamilies=['publications','github'],examples=[],
        versionVariants=[],missingVersionEdgeOccurrences=1,acceptedPredicates={'cites':2},equivalenceApproved=False)


def lexical(rows: list[dict]) -> tuple[dict,dict]:
    """Make a pinned selected lexical block and its original compact dossier."""
    ids=sorted(r['occurrenceID'] for r in rows);cls=rows[0]['ontologyClass'];key=['lexical_similarity_only',cls,'example']
    dossier=dict(blockID=m.candidates.token(key),key=key,ontologyClass=cls,occurrenceIDs=ids,
        members=[m.review.compact_member(r) for r in rows],existingBlockFlags=['unknown_version'])
    pilot=dict(blockID=dossier['blockID'],key=key,ontologyClass=cls,occurrenceIDs=ids,
        membershipSha256=m.candidates.token(ids),dossierBlockSha256=m.candidates.token(dossier),existingFlags=['unknown_version'],
        incidentAcceptedPredicates=['mentionsTool'],identityDecision='unadjudicated')
    return pilot,dossier


class PilotTests(unittest.TestCase):
    def setUp(self):
        """Disable networking and load only the frozen schema specification and fixtures."""
        self.enterContext(patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK')))
        self.enterContext(patch.object(socket.socket,'connect_ex',side_effect=AssertionError('NETWORK')))
        self.schema=json.loads(m.SCHEMA.read_bytes())
        self.nodes=[node('a',doi='10.1234/example'),node('b',curated=False,doi='10.1234/example')]
        self.rows=[occurrence(n) for n in self.nodes]
        self.groups=m.select_groups([(1,hub())],{'pilotQueue':[]},{})

    def prepare(self,groups=None,nodes=None,rows=None,edges=None,native=None,derived=None):
        """Assert complete input preservation around the pure package builder."""
        args=[self.groups if groups is None else groups,dict(nodes=self.nodes if nodes is None else nodes,edges=edges or []),
            self.rows if rows is None else rows,native or [],derived or [],SPEC,self.schema]
        before=deepcopy(args);result=m.prepare(*args);self.assertEqual(args,before);return result

    def test_selection_and_deduplication_without_transitive_union(self):
        """Exact memberships collapse cases; partial overlaps and all original groups survive."""
        p,d=lexical(self.rows)
        groups=m.select_groups([(1,hub()),(2,hub(tier='B')),(3,hub(('b','c')))],{'pilotQueue':[p]},{d['blockID']:d})
        cases=m.cases_for(groups)
        self.assertEqual(len(groups),4);self.assertEqual(len(cases),2)
        self.assertEqual(sorted(len(c['originalCandidateIDs']) for c in cases),[1,3])
        self.assertEqual(m.cases_for(groups[::-1]),cases)
        bad=deepcopy(p);bad['membershipSha256']='changed'
        with self.assertRaisesRegex(ValueError,'MEMBERSHIP_HASH_DRIFT'):
            m.select_groups([],{'pilotQueue':[bad]},{d['blockID']:d})

    def test_context_and_null_ledger_preserve_scope_versions_predicates(self):
        """Shared record/locator scopes and unchanged weak predicates are review data only."""
        groups=m.select_groups([(1,hub()),(2,hub(tier='B'))],{'pilotQueue':[]},{})
        e=edge('ref','a','b');e['attributes']={'versionSpec':'==1'}
        result=self.prepare(groups=groups,edges=[e])
        self.assertEqual(len(result['cases']),1)
        self.assertEqual(result['relations'][0]['acceptedPredicate'],'cites')
        self.assertEqual(result['relations'][0]['attributes']['value'],{'versionSpec':'==1'})
        self.assertTrue(all(r['canonicalID'] is None and r['decisionStatus']=='unreviewed' for r in result['ledger']))
        self.assertEqual(len(result['ledger'][0]['originalCandidateIDs']),2)
        scopes=result['requests'][0]['payload']['case']['candidateContexts']
        self.assertEqual({c['scopeAndConflicts']['identityScope'] for c in scopes},{'entity_own_record','literal_locator'})

    def test_generic_specific_and_missing_version_remain_unreviewed(self):
        """Label agreement cannot adjudicate generic architecture versus trained model."""
        nodes=[node('generic','MLModel',name='LSTM',description='Generic architecture'),node('trained','MLModel',name='LSTM',description='Trained on site A')]
        rows=[occurrence(n) for n in nodes];rows[1]['versions']={'version':'v1'}
        p,d=lexical(rows);groups=m.select_groups([],{'pilotQueue':[p]},{d['blockID']:d})
        result=self.prepare(groups=groups,nodes=nodes,rows=rows)
        self.assertTrue(all(r['decisionStatus']=='unreviewed' for r in result['ledger']))
        self.assertEqual(result['occurrences'][1]['fields']['versions']['value'],{'version':'v1'})
        self.assertEqual(result['cases'][0]['candidateContexts'][0]['scopeAndConflicts']['existingFlags'],['unknown_version'])

    def test_evidence_truncation_duplicate_quotes_and_request_bound(self):
        """Full membership survives truncation; oversized requests are held, not subsetted."""
        for n in self.nodes:n['evidence']['evidenceText']='same quote '*300
        rows=[occurrence(n) for n in self.nodes]
        result=self.prepare(rows=rows)
        ev=[o['evidence'][0] for o in result['occurrences']]
        self.assertTrue(all(e['truncated'] and len(e['excerpt'])==1600 for e in ev))
        self.assertEqual(ev[0]['quoteSha256'],ev[1]['quoteSha256'])
        self.assertNotEqual(ev[0]['evidenceID'],ev[1]['evidenceID'])
        with patch.object(m,'MAX_REQUEST_BYTES',1):held=self.prepare(rows=rows)
        self.assertIsNone(held['requests'][0]['payload']);self.assertTrue(held['requests'][0]['requestSizeExceeded'])
        self.assertEqual(held['cases'][0]['occurrenceIDs'],['a','b'])

    def test_missing_context_and_native_derived_edge_pointers(self):
        """Missing node evidence flags review; selected edge sidecars keep their exact IDs."""
        self.nodes[1].pop('evidence');rows=[occurrence(n) for n in self.nodes]
        e=edge('ref','a','b');e.pop('evidence')
        native=dict(kind='edges',graphID='ref',nativeRecord={'boundEvidence':[{'evidenceText':'accepted native quote'}]},provenance={'family':'publications'})
        native['nativeRecordSha256']=m.candidates.token(native['nativeRecord'])
        derived=dict(disposition='emitted',edgeID='ref',evidence=[{'evidenceText':'accepted derived quote'}])
        result=self.prepare(rows=rows,edges=[e],native=[(7,native)],derived=[(8,derived)])
        self.assertEqual(result['requests'][0]['missingContextOccurrenceIDs'],['b'])
        self.assertEqual(result['requests'][0]['readiness'],'human_context_review_required')
        self.assertEqual(result['relations'][0]['evidenceCount'],2)
        native['nativeRecordSha256']='drift'
        with self.assertRaisesRegex(ValueError,'NATIVE_HASH_DRIFT'):self.prepare(rows=rows,edges=[e],native=[(7,native)])

    def test_class_hash_and_duplicate_occurrence_fail_closed(self):
        """Do not repair changed memberships, ontology classes or original snapshot records."""
        with self.assertRaisesRegex(ValueError,'DUPLICATE_OCCURRENCE'):self.prepare(rows=self.rows+[self.rows[0]])
        bad=deepcopy(self.rows);bad[0]['snapshotRecordSha256']='changed'
        with self.assertRaisesRegex(ValueError,'SNAPSHOT_RECORD_DRIFT'):self.prepare(rows=bad)
        nodes=deepcopy(self.nodes);nodes[1]['class']='Repository'
        with self.assertRaisesRegex(ValueError,'CANDIDATE_CLASS_DRIFT'):self.prepare(nodes=nodes)
        self.assertEqual(self.prepare(),self.prepare(nodes=self.nodes[::-1],rows=self.rows[::-1]))

    def test_recommendation_schema_abstention_and_closed_world_citations(self):
        """Valid recommendations remain non-adjudicated; foreign IDs and unsupported claims fail."""
        request=self.prepare()['requests'][0]
        rec=dict(status='recommendation_only',caseID=request['caseID'],caseSha256=request['caseSha256'],contextSha256=request['payload']['contextSha256'],
            assessments=[],unassessedOccurrenceIDs=['a','b'],abstentionReason='Insufficient granularity context')
        m.validate_recommendation(rec,request,self.schema)
        bad=deepcopy(rec);bad['canonicalID']='not-allowed'
        from jsonschema import ValidationError
        with self.assertRaises(ValidationError):m.validate_recommendation(bad,request,self.schema)
        bad=deepcopy(rec);bad['unassessedOccurrenceIDs']=['a']
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_RECOMMENDATION_COVERAGE'):m.validate_recommendation(bad,request,self.schema)
        rec['assessments']=[dict(occurrenceIDs=['a','b'],identityLevel='reference_target',recommendation='shared_reference_target_only',
            granularityAssessment='record only',versionAssessment='unknown',ownerReferenceAssessment='targets, not owners',
            evidenceIDs=[request['payload']['occurrences'][0]['evidence'][0]['evidenceID']],conflictEvidenceIDs=[],rationale='Review candidate only',missingInformation=['version'])]
        rec['unassessedOccurrenceIDs']=[];m.validate_recommendation(rec,request,self.schema)
        changed=deepcopy(request);changed['payload']['occurrences'][0]['evidence'][0]['excerpt']='changed context'
        with self.assertRaisesRegex(ValueError,'RECOMMENDATION_CONTEXT_DRIFT'):m.validate_recommendation(rec,changed,self.schema)
        rec['assessments'][0]['evidenceIDs']=['invented']
        with self.assertRaisesRegex(ValueError,'UNKNOWN_EVIDENCE_CITATION'):m.validate_recommendation(rec,request,self.schema)

    def test_fixture_io_hashes_determinism_and_nonmutation(self):
        """Run packaging only against tiny temporary inputs, never the actual corpus."""
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);v2=root/'v2';v2.mkdir();prepared=root/'prepared';prepared.mkdir();review=root/'review';review.mkdir();frozen=root/'frozen';frozen.mkdir()
            def write(path,value):
                """Write canonical fixture bytes."""
                path.write_bytes(m.identity.encoded(value))
            (prepared/'occurrences.jsonl').write_bytes(b'\n'.join(m.identity.encoded(r) for r in self.rows)+b'\n')
            write(prepared/'manifest.json',{'outputHashes':{'occurrences.jsonl':m.identity.sha(prepared/'occurrences.jsonl')}})
            (review/'review-dossier.jsonl').write_text('')
            (frozen/'native.jsonl').write_text('');(frozen/'derivation-provenance.jsonl').write_text('')
            write(v2/'inventory.json',{'pilotQueue':[]});(v2/'shared-reference-hubs.jsonl').write_bytes(m.identity.encoded(hub())+b'\n')
            manifest=dict(version=m.opportunities.VERSION,outputHashes={p.name:m.identity.sha(p) for p in v2.iterdir()},
                inputHashes={str(p):m.identity.sha(p) for p in (prepared/'manifest.json',review/'review-dossier.jsonl')},
                implementationSha256=m.identity.sha(Path(m.opportunities.__file__)),sharedReferenceImplementationSha256=m.identity.sha(Path(shared.__file__)))
            write(v2/'manifest.json',manifest)
            before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with patch.object(m,'INPUT',v2),patch.object(m,'INPUT_PIN',m.identity.sha(v2/'manifest.json')),patch.object(m,'OUTPUT',root/'out'/'v1'),patch.object(m.review,'INPUT',prepared),patch.object(m.review,'OUTPUT',review),patch.object(m.identity,'ROOT',frozen),patch.object(m.identity,'verified_inputs',return_value=(dict(nodes=self.nodes,edges=[]),SPEC,frozen/'native.jsonl',{})):
                a=root/'out'/'a';b=root/'out'/'b';m.run(a);m.run(b)
                self.assertEqual({p.name:p.read_bytes() for p in a.iterdir()},{p.name:p.read_bytes() for p in b.iterdir()})
                self.assertTrue(all(Path(p).read_bytes()==v for p,v in before.items()))
                with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):m.run(a)
                (v2/'shared-reference-hubs.jsonl').write_text('drift')
                with self.assertRaisesRegex(ValueError,'INPUT_HASH_DRIFT'):m.run(root/'out'/'c')
                self.assertFalse((root/'out'/'c').exists())


if __name__=='__main__':unittest.main()
