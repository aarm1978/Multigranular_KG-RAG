"""Focused exact-first sensitivity tests; no provider or semantic judgments."""

from fractions import Fraction
from itertools import combinations
import json
import random
import unittest
import zipfile

from src.extraction.llm.publications import scierc_overlap_matching as m
from src.extraction.llm.publications import scierc_postrun_evaluation as prior
from src.extraction.llm.publications import scierc_overlap_analysis as analysis


def entity(identity,span,label="Method",doc="fixture",sentence=0):
    """Construct a minimal mechanical item."""
    return {"id":identity,"spans":[list(span)],"label":label,"documentID":doc,"sentenceIndices":[sentence]}


def relation(identity,head,tail,label="USED-FOR",doc="fixture",sentence=0):
    """Construct relation spans independently of entity-type metadata."""
    return {"id":identity,"spans":[list(head),list(tail)],"label":label,"documentID":doc,"sentenceIndices":[sentence,sentence]}


class MatchingTests(unittest.TestCase):
    """Protect only the new mechanical correspondence contract."""

    def test_exact_lock_precedes_overlap_cardinality(self):
        """An exact match cannot be displaced to increase residual correspondence count."""
        result=m.match_layer([entity("p1",(0,1)),entity("p2",(0,0))],
                             [entity("g1",(0,1)),entity("g2",(1,2))],"entity")
        self.assertEqual(result["locked"],[("p1","g1")]); self.assertEqual(result["selected"],[])

    def test_cardinality_precedes_weight(self):
        """Conflicts are solved globally, not by greedily taking the largest edge."""
        edges={("p1","g1"):Fraction(1),("p1","g2"):Fraction(1,10),("p2","g1"):Fraction(1,10)}
        self.assertEqual(m.maximum_matching(edges),[("p1","g2"),("p2","g1")])

    def test_weight_precedes_lexical_order(self):
        """Equal-cardinality solutions prefer larger exact rational sum."""
        edges={("a","a"):Fraction(1,3),("a","b"):Fraction(1,2),("b","a"):Fraction(1,2),("b","b"):Fraction(1,3)}
        self.assertEqual(m.maximum_matching(edges),[("a","b"),("b","a")])

    def test_stable_lexical_ties(self):
        """Input insertion order cannot change the unique lexical pair-set result."""
        pairs=[("a","a"),("a","b"),("b","a"),("b","b")]
        for order in (pairs,list(reversed(pairs))):
            self.assertEqual(m.maximum_matching({pair:Fraction(1) for pair in order}),[("a","a"),("b","b")])

    def test_small_graphs_against_exhaustive_objective(self):
        """Check the cardinality/IoU/lexical objective against exhaustive small graphs."""
        rng=random.Random(17)
        for _ in range(25):
            edges={(p,g):Fraction(rng.randint(1,3),3) for p in ("a","b","c") for g in ("x","y","z") if rng.random()<0.7}
            candidates=[]; pairs=sorted(edges)
            for size in range(4):
                for subset in combinations(pairs,size):
                    if len({p for p,g in subset})==len({g for p,g in subset})==size:
                        candidates.append(subset)
            best=min(candidates,key=lambda pairs:(-len(pairs),-sum((edges[p] for p in pairs),Fraction()),pairs))
            self.assertEqual(m.maximum_matching(edges),list(best))

    def test_document_sentence_type_isolation(self):
        """Same spans cannot bypass document, sentence or entity-type boundaries."""
        p=entity("p",(1,2))
        for g in (entity("g",(2,3),doc="other"),entity("g",(2,3),sentence=1),entity("g",(2,3),label="Task"),entity("g",(3,4))):
            self.assertEqual(m.orientations(p,g,"entity"),[])
        self.assertEqual(m.iou((1,2),(2,3)),Fraction(1,3))

    def test_relation_direction_and_no_endpoint_type_requirement(self):
        """Directed reversals fail; symmetric reversals match without entity types."""
        p=relation("p",(0,1),(5,6)); g=relation("g",(6,7),(1,2))
        p["endpointEntityTypes"]=["Method","Task"]; g["endpointEntityTypes"]=["Material","Generic"]
        self.assertEqual(m.orientations(p,g,"relation"),[])
        p["label"]=g["label"]="COMPARE"
        self.assertEqual(m.orientations(p,g,"relation"),[("swapped",Fraction(1,3))])
        g["label"]="CONJUNCTION"
        self.assertEqual(m.orientations(p,g,"relation"),[])

    def test_orientation_ties_retained(self):
        """Both symmetric orientations remain visible; direct wins an exact tie."""
        options=m.orientations(relation("p",(0,2),(1,3),"COMPARE"),relation("g",(1,2),(1,2),"COMPARE"),"relation")
        self.assertEqual([name for name,score in options],["direct","swapped"])
        self.assertEqual(options[0][1],options[1][1])

    def test_nonexclusive_flags(self):
        """Label and direction flags can overlap for the same exact endpoint pair."""
        p=relation("p",(0,1),(5,6)); g=relation("g",(5,6),(0,1),"PART-OF")
        self.assertEqual(m.discrepancy_flags(p,g,"relation"),["exact_endpoints_different_label","exact_endpoints_direction_reversal"])
        p["label"]=g["label"]="COMPARE"
        self.assertEqual(m.discrepancy_flags(p,g,"relation"),[])
        self.assertEqual(m.discrepancy_flags(entity("p",(0,1)),entity("g",(0,1),"Task"),"entity"),["exact_span_different_type"])

    def test_supports_are_not_reduced(self):
        """Matching leaves both complete item collections unchanged."""
        ps=[entity("p1",(0,1)),entity("p2",(1,2))]; gs=[entity("g",(0,2))]
        before=m.a.canonical_json([ps,gs]); result=m.match_layer(ps,gs,"entity")
        self.assertEqual(m.a.canonical_json([ps,gs]),before)
        self.assertEqual(len(result["selected"])+len(result["unmatchedPredictions"]),2)
        self.assertEqual(len(result["selected"])+len(result["unmatchedGold"]),1)
        self.assertEqual(len(result["eligible"]),2)

    def test_accepted_input_artifact_bindings_unchanged(self):
        """Check directly consumed A/B/decision/scorer identities, not historical audits."""
        manifest=prior.runner.read(prior.MANIFEST)
        for item in manifest["projections"]: prior.verify(item)
        decision=str(prior.DECISIONS.relative_to(prior.a.PROJECT_ROOT))
        prior.verify(next(item for item in manifest["bindings"] if item["path"]==decision))
        results=prior.runner.read(prior.OUT/"metrics.json")
        prior.verify(results["projectionManifest"]); prior.verify(results["unchangedScorer"])

    def test_materialized_review_covers_all_matches_and_unmatched(self):
        """Every additional correspondence and residual item is exported unjudged."""
        report=prior.runner.read(analysis.OUT/"aggregate_report.json")
        rows=[json.loads(line) for line in (analysis.REVIEW/"review.jsonl").read_bytes().splitlines()]
        self.assertEqual(len({r["caseID"] for r in rows}),len(rows))
        self.assertTrue(all(r["semanticJudgment"] is None and r["reviewerNotes"] is None for r in rows))
        for layer in ("entity","relation"):
            metrics=report["metrics"][layer]
            selected=[r for r in rows if r["layer"]==layer and r["category"]=="overlap_pair" and r["selected"]]
            self.assertEqual(len(selected),metrics["additionalMatches"])
            pairs=[(r["documentID"],r["prediction"]["id"],r["gold"]["id"]) for r in selected]
            self.assertEqual(len({(d,p) for d,p,g in pairs}),len(pairs))
            self.assertEqual(len({(d,g) for d,p,g in pairs}),len(pairs))
            for category,key in (("unmatched_prediction","FP"),("unmatched_gold","FN")):
                self.assertEqual(sum(r["layer"]==layer and r["category"]==category for r in rows),metrics["overlapSensitivity"][key])
            for support in ("goldSupport","predictionSupport"):
                self.assertEqual(metrics["strictA"][support],metrics["overlapSensitivity"][support])

    def test_zip_and_manifest_inputs_unchanged(self):
        """The shareable archive binds all files and accepted inputs remain unchanged."""
        manifest=prior.runner.read(analysis.OUT/"manifest.json")
        for item in manifest["inputs"]+manifest["reviewArtifacts"]+[manifest["aggregateReport"]]: prior.verify(item)
        with zipfile.ZipFile(analysis.REVIEW/"scierc_overlap_review_v0.1.0.zip") as archive:
            self.assertIsNone(archive.testzip())
            package=json.loads(archive.read("package_manifest.json"))
            for name,binding in package["files"].items():
                self.assertEqual(prior.a.sha256_bytes(archive.read(name)),binding["sha256"])
