"""Focused offline replacement and derived-review regression checks."""
import copy
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from src.evaluation import source_local_supplemental_review as r


class ReviewTests(unittest.TestCase):
    def setUp(self):
        """Build a tiny paired fixture and prohibit networking."""
        for name in ('connect', 'connect_ex'):
            p=patch.object(socket.socket,name,side_effect=AssertionError('NO_NETWORK'))
            p.start();self.addCleanup(p.stop)
        self.entries=[dict(identity={'requestID':rid},ownerID='owner',family='github',groupID=str(n))
                      for n,rid in enumerate(['other',r.retry.REQUEST_ID])]
        self.receipts={'other':{'providerResponse':dict(id='old-complete',status='completed')},
            r.retry.REQUEST_ID:{'providerResponse':dict(id=r.retry.RESPONSE_ID,status='incomplete',
                incomplete_details={'reason':'max_output_tokens'})}}
        self.supp=dict(id=r.SUPPLEMENT_ID,status='completed')
        p=patch.object(r,'SUPPLEMENT_SHA',r.digest(r.canonical(self.supp)));p.start();self.addCleanup(p.stop)

    def select(self):
        """Select the two-request synthetic equivalent."""
        return r.select(self.entries,self.receipts,self.supp,expected_count=2)

    def test_exact_replacement_preserves_originals(self):
        """Selection changes only the designated derived response."""
        original=copy.deepcopy(self.receipts)
        selected=self.select()
        self.assertEqual(selected['other']['id'],'old-complete')
        self.assertEqual(selected[r.retry.REQUEST_ID],self.supp)
        self.assertEqual(self.receipts,original)

    def test_missing_duplicate_and_hash_mismatch(self):
        """Fail closed on missing receipts, repeated identities or altered responses."""
        del self.receipts['other']
        with self.assertRaisesRegex(ValueError,'MISSING_OR_EXTRA'):self.select()
        self.entries[0]=self.entries[1]
        with self.assertRaisesRegex(ValueError,'DUPLICATE_OR_MISSING'):self.select()

    def test_hash_mismatch(self):
        """A claimed response ID cannot conceal changed supplemental bytes."""
        self.supp['extra']='changed'
        with self.assertRaisesRegex(ValueError,'SUPPLEMENT_HASH'):self.select()

    def test_invalid_evidence_is_reported_and_blocks_owner(self):
        """Every selected request is validated; a failure prevents complete consolidation."""
        with tempfile.TemporaryDirectory() as tmp:
            destination=Path(tmp)/'review'
            bundles={e['identity']['requestID']:{} for e in self.entries}
            with patch.object(r.retry,'validate_response',side_effect=ValueError('evidence mismatch')) as validate, \
                 patch.object(r.semantic,'consolidate') as consolidate:
                result=r.derive(self.entries,bundles,self.select(),destination)
            self.assertEqual(validate.call_count,2)
            self.assertEqual(result['counts']['failedValidations'],2)
            self.assertEqual(result['counts']['incompleteOwners'],1)
            consolidate.assert_not_called()
            with self.assertRaises(FileExistsError):r.derive(self.entries,bundles,self.select(),destination)

    def test_successful_groups_use_native_consolidation_and_diagnostics(self):
        """Reuse native consolidation and retain held/rejected/unresolved diagnostics."""
        report=dict(nativeValidationView={'status':'projection_completed','decisions':[
            {'disposition':'held'},{'disposition':'rejected'}]},
            unresolvedAssertions=[{}],abstentions=[{}],zeroYield=False)
        owner=dict(nodes=[{}],edges=[{},{}],derivedConstructionInputs=[],zeroYield=False)
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(r.retry,'validate_response',return_value=report), \
             patch.object(r.semantic,'consolidate',return_value=owner) as consolidate:
            result=r.derive(self.entries,{e['identity']['requestID']:{} for e in self.entries},
                            self.select(),Path(tmp)/'review')
            self.assertEqual(result['counts']['completeOwners'],1)
            self.assertEqual(result['counts']['nodes'],1)
            self.assertEqual(result['counts']['edges'],2)
            self.assertEqual(result['decisionDispositions'],{'held':2,'rejected':2})
            self.assertEqual(result['counts']['unresolvedAssertions'],2)
            consolidate.assert_called_once()

    def test_supplement_revalidated_not_trusted_from_usable_flag(self):
        """Existing usable status cannot bypass the original evidence validator."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/r.retry.OUTPUT;folder.mkdir(parents=True)
            prepared={'body':{}}
            intent=dict(requestID=r.retry.REQUEST_ID,originalResponseID=r.retry.RESPONSE_ID,
                originalJobID='job-000003',queueSha256=r.retry.QUEUE_SHA,runManifestSha256=r.retry.files.RUN_SHA,
                bundleSha256=r.retry.BUNDLE_SHA,providerBodySha256=r.digest(r.canonical({})),
                providerParameterChanges={},timeoutSeconds=600,maxRetries=0,authorizedPosts=1,sdkVersion='1.109.1')
            self.supp['usage']={}
            sha=r.digest(r.canonical(self.supp))
            outcome=dict(status='validated_supplemental_response',usable=True,responseID=r.SUPPLEMENT_ID,
                usage={},responseSha256=sha,integrated=False,kgAuthorization=False)
            for name,value in [('intent',intent),('outcome',outcome),('response',self.supp),('semantic-replay',{})]:
                (folder/(name+'.json')).write_text(json.dumps(value))
            before={p:p.read_bytes() for p in folder.iterdir()}
            with patch.object(r,'SUPPLEMENT_SHA',sha),patch.object(r.retry,'validate_response',side_effect=ValueError('invalid evidence')):
                with self.assertRaisesRegex(ValueError,'invalid evidence'):r.load_supplement(root,prepared)
            self.assertEqual(before,{p:p.read_bytes() for p in folder.iterdir()})


if __name__=='__main__':unittest.main()
