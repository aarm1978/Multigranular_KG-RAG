"""Four offline groups against the frozen ontology, without corpus execution."""

from __future__ import annotations

from copy import deepcopy
import unittest

from src.extraction.llm.semantic_target_profiles import check_target, get_profile, load_ontology


class NonpublicationTargetProfileTests(unittest.TestCase):
    """Check only the frozen target projection and structural gate interface."""

    def test_exact_allowlists_and_ontology_correspondence(self) -> None:
        """Inventory IDs are explicit per source, never expanded from the TBox."""
        models = {"A-DOM03a", "A-DOM03b", "A-DOM03c", "A-DOM03d", "A-DOM03e"}
        expected = {
            "hydroshare": ({"A-DOM04", "A-D12", "A-DOM02", "A-C11", "A-C01"} | models,
                           {"C-D16", "C-D17", "C-D18", "C-D24", "C-D25", "C-D26", "C-D22", "D-17"}),
            "github": ({"A-C07", "A-DOM02", "A-D01", "A-C11", "A-C08", "A-DOM13", "A-C10", "A-P13"} | models,
                       {"C-C07", "C-C11", "C-C22", "D-22", "C-C21", "C-C23", "C-C15", "C-C10", "C-C08", "C-C20", "C-C09", "C-C16"}),
            "ciroh_hub": ({"A-DOM02", "A-D01", "A-P13", "A-C01", "A-DC05", "A-DC06", "A-C11", "A-DC08", "A-DOM12"} | models,
                          {"C-DC17", "C-DC19", "C-DC07", "C-DC16", "C-DC27", "C-DC28", "D-22", "C-DC20", "C-DC10", "C-DC09", "C-DC12", "C-DC11"}),
        }
        ontology = load_ontology()
        declarations = {r["id"]: r for r in ontology["classes"] + ontology["relations"]}
        for family, (entities, relations) in expected.items():
            profile = get_profile(family)
            self.assertEqual(set(profile["entities"]), entities)
            self.assertEqual(set(profile["relations"]), relations)
            for identifier, record in {**profile["entities"], **profile["relations"]}.items():
                self.assertEqual(record["declaration"], declarations[identifier])
            self.assertEqual(profile["ontologyVersion"], "0.1.6")
        self.assertEqual(get_profile("hydroshare")["relations"]["C-D26"]["declaration"]["name"], "mentionsModel")
        self.assertEqual(declarations["D-26"]["name"], "mentions")

    def test_signatures_direction_and_declared_unions(self) -> None:
        """Use exact relation identity, ontology unions and concrete inheritance."""
        cases = [("hydroshare", "C-D16", "containsVariable", "A-D01", "A-DOM04"),
                 ("hydroshare", "C-D26", "mentionsModel", "A-D01", "A-DOM03e"),
                 ("github", "D-22", "implementedBy", "A-DOM02", "A-C01"),
                 ("github", "D-22", "implementedBy", "A-DOM03a", "A-C01"),
                 ("ciroh_hub", "C-DC09", "explainsWorkflow", "A-DC01", "A-C11"),
                 ("ciroh_hub", "C-DC09", "explainsWorkflow", "A-DC05", "A-C11"),
                 ("ciroh_hub", "C-DC17", "catalogs", "A-DC01", "A-DOM02"),
                 ("ciroh_hub", "C-DC17", "catalogs", "A-DC01", "A-DOM03d"),
                 ("ciroh_hub", "C-DC19", "hasComponent", "A-DOM03b", "A-DOM02"),
                 ("ciroh_hub", "C-DC19", "hasComponent", "A-DOM02", "A-DOM03c")]
        for family, identifier, name, source, target in cases:
            with self.subTest(identifier=identifier, source=source, target=target):
                checked = check_target(family, identifier, relation_name=name, source_class_id=source, target_class_id=target)
                self.assertTrue(checked["structuralScopePass"])
                self.assertFalse(checked["kgAuthorization"])
        for identifier, name in (("C-C16", "implementsMethod"),):
            gates = {g: True for g in get_profile("github")["relations"][identifier]["requiredGates"]}
            for source in ("A-C01", "A-DOM02"):
                self.assertTrue(check_target("github", identifier, relation_name=name,
                    source_class_id=source, target_class_id="A-P13", gates=gates)["structuralScopePass"])
        for source, target, name in (("A-DOM04", "A-D01", "containsVariable"),
                                     ("A-D01", "A-DOM05", "containsVariable"), ("A-D01", "A-DOM04", "mentions")):
            self.assertFalse(check_target("hydroshare", "C-D16", relation_name=name,
                source_class_id=source, target_class_id=target)["structuralScopePass"])

    def test_conditional_inactive_seed_parent_and_pipeline_targets(self) -> None:
        """Preserve bounded evidence conditions and non-model generation modes."""
        hydro = get_profile("hydroshare")
        self.assertEqual(hydro["entities"]["A-D12"]["evidenceSources"], ["README"])
        self.assertFalse(check_target("hydroshare", "A-D12")["structuralScopePass"])
        self.assertTrue(check_target("hydroshare", "A-D12", gates={"explicit_readme_measurement": True})["structuralScopePass"])
        github = get_profile("github")
        seed = github["entities"]["A-C07"]
        self.assertEqual(seed["mode"], "controlled_vocabulary_seed")
        self.assertEqual(seed["categoryCount"], 6)
        self.assertFalse(check_target("github", "A-C07")["structuralScopePass"])
        self.assertTrue(check_target("github", "A-C07", model_authored=False)["structuralScopePass"])
        self.assertTrue(github["relations"]["C-C07"]["modelAuthorable"])
        self.assertIn("repository_specific_purpose_evidence", github["relations"]["C-C07"]["requiredGates"])
        self.assertFalse(github["entities"]["A-P13"]["modelAuthorable"])
        self.assertEqual(github["relations"]["C-C16"]["unresolvedDisposition"], "unresolved_endpoint_non_KG")
        self.assertIn("own_repository_product", github["entities"]["A-C10"]["requiredGates"])
        hub = get_profile("ciroh_hub")
        for identifier in ("A-DC08", "A-DOM12"):
            record = hub["entities"][identifier]
            self.assertEqual(record["parentRelationPaths"], [["C-DC20"], ["C-DC20", "C-DC10"]])
            self.assertFalse(check_target("ciroh_hub", identifier)["structuralScopePass"])
            gates = {g: True for g in record["requiredGates"]}
            self.assertTrue(check_target("ciroh_hub", identifier, gates=gates)["structuralScopePass"])
            gates["accepted_required_parent_relations"] = "true"
            self.assertFalse(check_target("ciroh_hub", identifier, gates=gates)["structuralScopePass"])
        for family in ("hydroshare", "github", "ciroh_hub"):
            for identifier in ("A-D13", "C-D29", "D-26", "A-DOM01", "A-DOM03", "A-DOM09"):
                self.assertFalse(check_target(family, identifier)["structuralScopePass"])

    def test_fail_closed_determinism_and_immutability(self) -> None:
        """Changes to authority/signature inputs cannot silently broaden scope."""
        ontology = load_ontology()
        before = deepcopy(ontology)
        profile = get_profile("github", ontology=ontology)
        self.assertEqual(profile, get_profile("github"))
        self.assertEqual(ontology, before)
        profile["relations"]["C-C16"]["declaration"]["domain"].append("DatasetResource")
        self.assertEqual(get_profile("github")["relations"]["C-C16"]["declaration"]["domain"], ["Repository", "Tool"])
        for field, value in (("domain", "DatasetResource"), ("range", "Concept"), ("name", "wrong")):
            changed = deepcopy(ontology)
            next(r for r in changed["relations"] if r["id"] == "C-C16")[field] = value
            with self.assertRaises(ValueError):
                get_profile("github", ontology=changed)
        with self.assertRaises(ValueError):
            get_profile("publication")
        for identifier in ("unknown", "A-DOM05", "C-C27"):
            self.assertFalse(check_target("github", identifier)["structuralScopePass"])
        flags = {"own_repository_product": True}
        before_flags = deepcopy(flags)
        checked = check_target("github", "A-C10", gates=flags)
        self.assertEqual(flags, before_flags)
        self.assertFalse(checked["structuralScopePass"])
        self.assertFalse(checked["semanticAcceptance"])
        self.assertFalse(checked["kgAuthorization"])


if __name__ == "__main__":
    unittest.main()
