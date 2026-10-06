"""Focused local-isolation tests; never load benchmark gold or dispatch a provider."""

from copy import deepcopy
from dataclasses import replace
import unittest

from src.extraction.llm.publications import scierc_postrun_projection as p
from src.extraction.llm.publications import scierc_postrun_evaluation as w


class ProjectionTests(unittest.TestCase):
    """Synthetic constraints plus unchanged-original-valid corpus regression."""

    def setUp(self):
        """Make one inconsistent entity and both dependent and independent edges."""
        self.doc=p.a.parse_processed_document({"doc_key":"fixture","sentences":[["A","B","C","D"]]},include_gold=False)
        self.payload={"documentID":"fixture","entities":[
            {"entityID":f"e{i}","entityType":"Method","mentionText":text,"spanStart":i-1,"spanEnd":i-1}
            for i,text in enumerate(["wrong","B","C"],1)],"relations":[
            {"relationID":"r1","relationType":"USED-FOR","sourceEntityID":"e1","targetEntityID":"e2"},
            {"relationID":"r2","relationType":"USED-FOR","sourceEntityID":"e2","targetEntityID":"e3"}]}

    def project(self,payload=None):
        """Serialize a fixture without normalizing field values."""
        return p.project(p.a.canonical_json(self.payload if payload is None else payload),self.doc)

    def test_local_and_dependency_exclusion_with_retention(self):
        """Exclude only direct mismatch and dependent edge, preserving order/values."""
        before=deepcopy(self.payload)
        kept,ledger=self.project()
        self.assertEqual(kept["entities"],self.payload["entities"][1:])
        self.assertEqual(kept["relations"],self.payload["relations"][1:])
        self.assertEqual([(r["recordID"],r["reasonKind"]) for r in ledger],[("e1","direct"),("r1","dependency")])
        self.assertEqual(self.payload,before)
        p.a.validate_prediction(kept,self.doc)

    def test_all_mismatches_not_first_only(self):
        """Independent mismatch locations are all enumerated, without intent inference."""
        self.payload["entities"][2]["mentionText"]="other"
        kept,ledger=self.project()
        self.assertEqual([e["entityID"] for e in kept["entities"]],["e2"])
        self.assertEqual(kept["relations"],[])
        self.assertEqual(len(ledger),4)

    def test_global_error_refusal_including_discardable_records(self):
        """Other defects cannot be hidden by local filtering."""
        cases=[]
        wrong=deepcopy(self.payload); wrong["documentID"]="elsewhere"; cases.append(wrong)
        duplicate=deepcopy(self.payload); duplicate["entities"].append(deepcopy(duplicate["entities"][0])); cases.append(duplicate)
        signature=deepcopy(self.payload); extra=deepcopy(signature["entities"][0]); extra["entityID"]="new"; signature["entities"].append(extra); cases.append(signature)
        dangling=deepcopy(self.payload); dangling["relations"][0]["targetEntityID"]="absent"; cases.append(dangling)
        boolean=deepcopy(self.payload); boolean["entities"][0]["spanStart"]=True; cases.append(boolean)
        bad=deepcopy(self.payload); bad["entities"][0]["spanEnd"]=999; cases.append(bad)
        duplicate_relation=deepcopy(self.payload); duplicate_relation["relations"].append(deepcopy(duplicate_relation["relations"][0])); cases.append(duplicate_relation)
        for value in cases:
            with self.subTest(value=value),self.assertRaises(Exception): self.project(value)

    def test_cross_sentence_dependency_is_blocker(self):
        """An excluded endpoint does not exempt an invalid direct relation."""
        self.doc=p.a.parse_processed_document({"doc_key":"fixture","sentences":[["A"],["B","C","D"]]},include_gold=False)
        with self.assertRaisesRegex(ValueError,"RELATION_CROSSES_SENTENCE_BOUNDARY"): self.project()

    def test_strict_json_and_schema(self):
        """Duplicate JSON keys, invalid types and extra fields are not repaired."""
        with self.assertRaises(ValueError): p.project(b'{"documentID":"a","documentID":"b"}',self.doc)
        with self.assertRaises(ValueError): p.project(b'NaN',self.doc)
        self.payload["extra"]=1
        with self.assertRaises(Exception): self.project()

    def test_gold_independent_projection(self):
        """Counterfactual synthetic gold cannot change either kept records or ledger."""
        raw=p.a.canonical_json(self.payload)
        changed=replace(self.doc,gold_entities=((0,0,"Task"),),gold_relations=((0,0,1,1,"COMPARE"),))
        self.assertEqual(p.project(raw,self.doc),p.project(raw,changed))

    def test_original_98_predictions_unchanged(self):
        """Read only source requests/model outputs for the originally valid documents."""
        candidate=w.runner.read(w.runner.CANDIDATE); checked=0
        for row in candidate["requests"]:
            root=w.runner.document_root(w.runner.ROOT,row["documentID"])
            if w.runner.read(root/"terminal.json")["terminalStatus"]!="completed_valid": continue
            raw=(root/"raw_model_output.bin").read_bytes()
            doc=w.source_document(w.runner.read(root/"provider_request.json"))
            kept,ledger=p.project(raw,doc)
            self.assertFalse(ledger)
            self.assertEqual(p.a.canonical_json(kept),p.a.canonical_json(w.runner.read(root/"validated_prediction.json")))
            self.assertEqual(p.a.canonical_json(kept),p.a.canonical_json(w.s._strict_json(raw)))
            checked+=1
        self.assertEqual(checked,98)
