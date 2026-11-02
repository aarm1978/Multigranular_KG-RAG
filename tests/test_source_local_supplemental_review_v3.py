"""Focused replay regression-stop and provenance tests; no provider operations."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from src.evaluation import source_local_supplemental_review_v3 as r


def report(disposition='held',binding='uncertain'):
    """Build minimal native report structure for comparison boundaries."""
    candidate=dict(candidateID='n',inventoryId='A-DOM02',evidence=[dict(sourceUnitID='u',evidenceText='q')])
    check=dict(candidateID='n',originalCandidate=candidate,sourceLocalCandidateID='local',kind='node',
               evidenceBindings=[dict(binding=dict(status=binding))],dependencies=[])
    decision=dict(candidateID='n',disposition=disposition,blockingReasons=['visibility'] if disposition=='held' else [])
    projection=dict(artifactFamily='ciroh_hub',owner={'endpointID':'o'},nodes=[],edges=[])
    if disposition=='accepted':projection['nodes']=[dict(candidateID='n',sourceLocalCandidateID='local',originalCandidate=candidate,
        boundEvidence=[dict(sourceUnitID='u',startOffsetInAuthority=0,endOffsetInAuthority=1,evidenceText='q')])]
    return dict(requestID='r',groupID='g',requestSha256='req',responseSha256='resp',responseBytesHex='7b7d',abstentions=[],quarantinedAbstentions=[],
        nativeValidationView=dict(originalReplay={'requestResult':{'request':{}},'validationResult':{'candidateChecks':[check]}},
        deferredSourceRecords=[],deferredEvidenceAssociations=[],projection=projection,decisions=[decision]))


class ComparisonTests(unittest.TestCase):
    def test_independent_recovery_is_causally_recorded(self):
        """A new bound span can explain admission without rewriting a candidate."""
        a=report();b=report('accepted','bound');original=deepcopy(a)
        rows=r.compare_group(a,b)
        self.assertEqual(rows[0]['cause'],'independent_lexical_binding')
        self.assertEqual(rows[0]['changedBindingCandidates'],['n'])
        self.assertEqual(a,original)

    def test_dependency_recovery_is_not_double_counted(self):
        """A dependent with unchanged own binding is attributed only to its ancestor."""
        a=report();b=report('accepted','bound')
        for view,disposition in ((a,'held'),(b,'accepted')):
            n=view['nativeValidationView'];check=deepcopy(n['originalReplay']['validationResult']['candidateChecks'][0])
            check.update(candidateID='dependent',dependencies=['n'],evidenceBindings=[{'binding':{'status':'bound'}}])
            check['originalCandidate']['candidateID']='dependent'
            n['originalReplay']['validationResult']['candidateChecks'].append(check)
            n['decisions'].append(dict(candidateID='dependent',disposition=disposition,blockingReasons=[]))
        rows=r.compare_group(a,b)
        self.assertEqual([x['cause'] for x in rows],['independent_lexical_binding','downstream_dependency'])

    def test_accepted_loss_or_evidence_change_stops(self):
        """No new lexical policy can silently remove or reidentify accepted assertions."""
        a=report('accepted','bound');b=report()
        with self.assertRaisesRegex(r.v2.RegressionStop,'PREVIOUSLY_ACCEPTED_LOST'):r.compare_group(a,b)
        b=deepcopy(a);b['nativeValidationView']['projection']['nodes'][0]['boundEvidence'][0]['startOffsetInAuthority']=10
        with self.assertRaisesRegex(r.v2.RegressionStop,'PREVIOUSLY_ACCEPTED_CHANGED'):r.compare_group(a,b)

    def test_quarantine_and_authentic_bytes_are_immutable(self):
        """Malformed abstentions remain non-evidence records with their exact fields."""
        a=report();a['quarantinedAbstentions']=[dict(original={'sourceUnitIDs':['invalid']},reasons=['invalid_abstention'])]
        b=deepcopy(a);b['quarantinedAbstentions']=[]
        with self.assertRaisesRegex(r.v2.RegressionStop,'IMMUTABLE_GROUP_DRIFT'):r.compare_group(a,b)
        b=deepcopy(a);b['responseBytesHex']='00'
        with self.assertRaisesRegex(r.v2.RegressionStop,'IMMUTABLE_GROUP_DRIFT'):r.compare_group(a,b)

    def test_unexplained_change_stops(self):
        """A changed disposition alone never demonstrates a classifier-induced recovery."""
        with self.assertRaisesRegex(r.v2.RegressionStop,'UNEXPLAINED_DECISION_CHANGE'):
            r.compare_group(report(),report('accepted','uncertain'))

    def test_metadata_normalization_is_narrow(self):
        """Only overlay version and replay-hash provenance are excluded from comparison."""
        self.assertEqual(r.normalized({'lexicalClassifierVersion':r.corrected.VERSION,'replaySha256':'x','sourceUnitID':'u'}),{'sourceUnitID':'u'})
        self.assertEqual(r.normalized({'lexicalClassifierVersion':'unknown'}),{'lexicalClassifierVersion':'unknown'})

    def test_output_refused_before_any_inputs_loaded(self):
        """No existing interpretation is overwritten even when inputs are unavailable."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/r.OUTPUT).mkdir(parents=True)
            with patch.object(r.v2,'load_frozen') as load:
                with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'):r.run(root)
                load.assert_not_called()


if __name__=='__main__':unittest.main()
