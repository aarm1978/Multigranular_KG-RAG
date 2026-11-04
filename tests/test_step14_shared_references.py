"""Small fixtures for exact provenance recovery and provisional reference hubs."""
from copy import deepcopy
import unittest

from tests import test_step14_alignment_opportunities as fixtures
from tests.test_step14_alignment_opportunities import node, edge, SPEC
from src.evaluation import step14_alignment_opportunities as m
from src.evaluation import step14_shared_references as hubs


def repository(nid='repo', repo_id=1):
    """Match the frozen repository_node/metadata_evidence field contract."""
    full_name=f'owner/project{repo_id}'; url='https://github.com/'+full_name
    n=node(nid,'Repository',family='github',repoId=repo_id,fullName=full_name,htmlUrl=url)
    n.update(canonicalKey=f'github-repo-id:{repo_id}',identityRegime='github_numeric_id',
             internalLineage=dict(phaseAField='repo root',phaseAVersion='1.1.0'),
             evidence=dict(sourceArtifact=url,sourceLocation='https://api.github.com/repos/'+full_name,
                           evidenceText='Repository metadata',extractionMethod='deterministic',version='epoch'))
    return n


def github_edge(eid, source, target, predicate='referencePublication', inventory='C-C18'):
    """Use original GitHub file evidence with an exact frozen SHA agreement."""
    e=edge(eid,source['id'],target,predicate,inventory);url=source['attributes']['htmlUrl'];sha='a'*40
    e['internalLineage']={'rawSource':'README.md'}
    e['evidence'].update(sourceArtifact=url+'/tree/'+sha,sourceLocation=url+'/blob/'+sha+'/README.md',version=sha)
    return e


class SharedReferenceTests(unittest.TestCase):
    setUp = fixtures.OpportunityTests.setUp
    inventory = fixtures.OpportunityTests.inventory
    def test_exact_root_recovery_and_negative_contracts(self):
        """No rawSource is required, but no ID-prefix or incomplete metadata fallback exists."""
        n=repository();self.assertIsNone(m.candidates.deterministic_family(n))
        self.assertEqual(m.github_root_family(n),'github')
        for field in ('canonicalKey','identityRegime','curationStatus'):
            bad=deepcopy(n);bad[field]='wrong';self.assertIsNone(m.github_root_family(bad))
        for field in ('sourceArtifact','sourceLocation','extractionMethod','evidenceText','version'):
            bad=deepcopy(n);bad['evidence'].pop(field);self.assertIsNone(m.github_root_family(bad))
        target=node('target',curated=False,doi='10.1234/paper')
        e=github_edge('e',n,'target')
        # Use the actual ontology signature name/ID, not a guessed relation ID.
        e['inventoryId']=next(r['id'] for r in SPEC['relations'] if r['name']=='referencePublication')
        result=self.inventory([n,target],[e])
        self.assertEqual(result['summary']['sourceProvenanceRecoveredByExactRootContract'],1)
        self.assertTrue(result['relationInventory'][0]['sourceProvenanceConfirmed'])
        self.assertEqual(result['relationInventory'][0]['predicate'],'referencePublication')
        file=node('file','RepoFile',family='github',curated=False);file['class']='File'
        e=github_edge('f',n,'file','hasFile',next(r['id'] for r in SPEC['relations'] if r['name']=='hasFile'))
        result=self.inventory([n,file],[e])
        self.assertEqual(result['relationInventory'][0]['signatureStatus'],'class_incompatible')

    def test_doi_shared_artifacts_stubs_duplicates_and_missing_provenance(self):
        """Repeated edges retain counts, but origins and target ownership are separate."""
        nodes=[node('p1'),node('p2'),node('t1',curated=False,doi='10.1234/x'),node('t2',curated=False,doi='10.1234/x')]
        edges=[edge('a','p1','t1'),edge('b','p1','t1'),edge('c','p2','t2')]
        result=self.inventory(nodes,edges);g=result['sharedReferenceGroups'][0]
        self.assertEqual(g['evidenceTier'],'A');self.assertEqual(g['distinctOriginatingArtifacts'],2)
        self.assertEqual(g['acceptedReferenceEdgeOccurrences'],3)
        self.assertEqual(g['uniqueArtifactToTargetReferences'],2)
        self.assertEqual(g['connectionScope'],'within_family')
        self.assertEqual(g['targetRepresentation'],'multiple_existing_nodes_or_stubs')
        self.assertEqual(g['distinctQuoteHashes'],1)
        self.assertFalse(g['matchingCuratedArtifactIDs'])
        nodes[1].pop('evidence')
        g=self.inventory(nodes,edges)['sharedReferenceGroups'][0]
        self.assertEqual(g['distinctOriginatingArtifacts'],1)
        self.assertEqual(g['unresolvedOriginEdgeOccurrences'],1)
        self.assertFalse(g['sharedByMultipleArtifacts'])
        self.assertEqual(result,self.inventory(list(reversed(nodes[:1]+[node('p2')]+nodes[2:])),list(reversed(edges))))

    def test_hydroshare_identity_vs_reference_literal(self):
        """Only resource-own IDs become A; a source URL never transfers identity."""
        target=node('d','DatasetResource',curated=False,resourceId='a'*32)
        self.assertEqual(hubs.target_keys(target),[('A','hydroshare','a'*32,'entity_own_record')])
        target['attributes']={'url':'https://www.hydroshare.org/resource/'+'a'*32+'/'}
        self.assertTrue(all(k[0]=='B' for k in hubs.target_keys(target)))
        target['attributes']={'name':'unknown','citation':'10.1234/paper'}
        self.assertTrue(all(k[0]=='C' for k in hubs.target_keys(target)))
        self.assertEqual(hubs.target_keys(target,['10.1234/paper'])[0][0],'B')

    def test_repository_scope_and_curated_matching(self):
        """Explicit roots match at repository-record scope; branches/clones stay locators."""
        owner=repository();url=owner['attributes']['htmlUrl']
        stub=node('stub','Repository',curated=False,htmlUrl=url)
        stub.update(identityRegime='github_repository_url',canonicalKey='url:'+url)
        rootkey=('A','github_repository_root',url,'repository_record_not_code_version')
        self.assertIn(rootkey,hubs.target_keys(owner));self.assertIn(rootkey,hubs.target_keys(stub))
        for suffix in ('/tree/main','/blob/main/code.py','.git'):
            variant=deepcopy(stub);variant['canonicalKey']='url:'+url+suffix;variant['attributes']['htmlUrl']=url+suffix
            self.assertTrue(all(k[0]=='B' for k in hubs.target_keys(variant)))
        e=edge('e','paper','stub','referencesRepository','C-P28')
        e['inventoryId']=next(r['id'] for r in SPEC['relations'] if r['name']=='referencesRepository' and 'Paper' in r['domain'])
        result=self.inventory([node('paper'),stub,owner],[e])
        g=result['sharedReferenceGroups'][0]
        self.assertEqual(g['matchingCuratedArtifactIDs'],['repo'])

    def test_dependency_versions_remain_ambiguous(self):
        """Ecosystem coordinates preserve constraints without declaring registry/release identity."""
        repo=repository();dep=node('dep','Dependency',curated=False,ecosystem='pypi',canonicalName='numpy')
        dep.update(identityRegime='ecosystem_package_name',canonicalKey='package:pypi:numpy')
        inv=next(r['id'] for r in SPEC['relations'] if r['name']=='dependsOn')
        edges=[github_edge('a',repo,'dep','dependsOn',inv),github_edge('b',repo,'dep','dependsOn',inv)]
        edges[0]['attributes']={'versionSpec':'>=1','ecosystem':'pypi'}
        edges[1]['attributes']={'versionSpec':'==2','ecosystem':'pypi'}
        g=self.inventory([repo,dep],edges)['sharedReferenceGroups'][0]
        self.assertEqual(g['evidenceTier'],'C');self.assertEqual(g['distinctOriginatingArtifacts'],1)
        self.assertEqual(len(g['versionVariants']),2);self.assertFalse(g['equivalenceApproved'])
        dep['attributes']['ecosystem']='npm';dep['canonicalKey']='package:npm:numpy'
        self.assertNotEqual(hubs.target_keys(dep)[0][2],g['identifierValue'])

    def test_snapshot_root_alias_and_cross_family(self):
        """Exact constructor evidence maps snapshot to one owner; arbitrary tree URLs do not."""
        repo=repository();t=node('t',curated=False,doi='10.1234/t');p=node('paper')
        e=github_edge('git',repo,'t');e['inventoryId']='C-C18'
        e['inventoryId']=next(r['id'] for r in SPEC['relations'] if r['name']=='referencePublication')
        result=self.inventory([repo,t,p],[e,edge('pub','paper','t')])
        g=result['sharedReferenceGroups'][0]
        self.assertEqual(g['connectionScope'],'cross_family');self.assertEqual(g['distinctOriginatingArtifacts'],2)
        self.assertEqual(g['targetRepresentation'],'one_shared_graph_node')
        e['evidence']['version']='wrong'
        g=self.inventory([repo,t,p],[e,edge('pub','paper','t')])['sharedReferenceGroups'][0]
        self.assertEqual(g['distinctOriginatingArtifacts'],1)
        self.assertEqual(g['unresolvedOriginEdgeOccurrences'],1)

    def test_explicit_mirror_and_unknown_origin_not_extra_referrers(self):
        """A declared materialized mirror is excluded, not counted as independent support."""
        p=node('paper');page=node('page','DocumentationPage',family='ciroh_hub')
        page['internalLineage']={'corpusPath':'pages/test'}
        t=node('target',curated=False,doi='10.1234/x');repo=repository()
        mirror=edge('mirror','page','repo','documents','C-DC13')
        mirror['attributes']={'mirrorKind':'materialized_repository_file','repositoryPath':'README.md'}
        page_ref=edge('ref','page','target','referencePublication','C-DC26')
        page_ref['evidence']['sourceArtifact']=page['evidence']['sourceArtifact']
        result=self.inventory([p,page,t,repo],[edge('paperref','paper','target'),page_ref,mirror])
        g=next(g for g in result['sharedReferenceGroups'] if g['identifierScheme']=='doi')
        self.assertEqual(g['distinctOriginatingArtifacts'],1)
        self.assertEqual(g['excludedMirrorArtifactIDs'],['page'])
        self.assertFalse(g['sharedByMultipleArtifacts'])

    def test_local_declaration_is_locator_and_never_own_doi(self):
        """Native evidence-bound literals remain weaker than typed deterministic IDs."""
        target=node('target','Tool',curated=False,name='software')
        native=dict(originalCandidate={'exactIdentifier':'https://example.org/tool'},
                    boundEvidence=[dict(evidenceText='See https://example.org/tool',sourceArtifact='paper:paper')])
        row=dict(kind='nodes',graphID='target',nativeRecord=native,nativeRecordSha256=m.candidates.token(native),provenance={'family':'publications'})
        inv=next(r['id'] for r in SPEC['relations'] if r['name']=='usesTool' and 'Repository' in r['domain'])
        repo=repository();e=github_edge('e',repo,'target','usesTool',inv)
        g=self.inventory([repo,target],[e],native=[row])['sharedReferenceGroups'][0]
        self.assertEqual(g['evidenceTier'],'B')
        self.assertEqual(g['acceptedPredicates'],{'usesTool':1})
        target.update(identityRegime='software_doi',canonicalKey='doi:10.1234/x',identityScope='source_local')
        self.assertFalse(any(k[0]=='A' for k in hubs.target_keys(target)))


if __name__=='__main__':
    unittest.main()
