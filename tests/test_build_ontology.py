"""Structural regression tests for the generated CIROH ontology."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = PROJECT_ROOT / "src/ontology/ontology_spec.yaml"
OWL_PATH = PROJECT_ROOT / "src/ontology/ciroh_ontology.owl"
BUILDER_PATH = PROJECT_ROOT / "src/ontology/build_ontology.py"
INVENTORY_PATH = PROJECT_ROOT / "docs/ontology_inventory.md"
HUB_OUTPUT_PATH = PROJECT_ROOT / "data/interim/documents/ciroh_hub_nodes_edges.json"
FROZEN_OUTPUT_HASHES = {
    PROJECT_ROOT / "data/interim/papers/publication_nodes_edges.json": "675049dae5c3dfed6f492ad0aa79e27fc1a9b37d0ecbc13ab3cf1a69cdb8efaf",
    PROJECT_ROOT / "data/interim/datasets/hydroshare_nodes_edges.json": "c76c1cf9c88fe2a91f4927bd3bd4fc03456e3a2a83190bd3d8c47076f2acb7e3",
    PROJECT_ROOT / "data/interim/coderepos/github_nodes_edges.json": "2f752295a7d465acd094672b0a5961ffd1fe5453d6d576fc497e284068d901a6",
    HUB_OUTPUT_PATH: "c106c410b6f84a2755d17cec4629b90d5b145c0813c2866005cb20bcea649602",
}

# Frozen Phase B outputs preserve several explicit narrative aliases/composite
# labels from their ontology-0.1.1 extraction contracts. They remain accepted
# compatibility spellings without rewriting any frozen graph.
FROZEN_NODE_COMPATIBILITY = {
    ("A-D06", "Subject"): "A-P04",
    ("A-D07→A-DOM09", "SpatialCoverage"): "A-DOM09",
    ("A-D08→A-DOM10", "TemporalCoverage"): "A-DOM10",
    ("A-C02", "File"): "A-C02",
    ("A-C06", "License"): "A-D05",
}
FROZEN_EDGE_COMPATIBILITY = {
    ("A-ID01 (ID-R1)", "hasIdentifier"): "ID-R1",
    ("C-D09 / A-AG-R2", "fundedBy"): "C-D09",
    ("C-DC05/A-AG", "hasContributor"): "C-DC05",
    ("D-05", "referencesDataset"): "C-C19",
}

NS = {
    "ciroh": "https://w3id.org/ciroh/ontology#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
}
RDF_ABOUT = f"{{{NS['rdf']}}}about"
RDF_RESOURCE = f"{{{NS['rdf']}}}resource"
GENERATED_CLASS_LOCAL_ALIASES = {"Methods": "Method", "Data": "DataDescription"}

# Narrative module IDs that consolidate into shared or canonical machine-readable
# ontology IDs. This is an explicit traceability registry, not a fuzzy matcher.
APPROVED_INVENTORY_ALIASES = {
    "A-C05": "A-AG01",
    "A-C06": "A-D05",
    "A-C09": "A-DOM13",
    "A-D06": "A-P04",
    "A-D07": "A-DOM09",
    "A-D08": "A-DOM10",
    "A-D11": "A-DOM04",
    "A-DC04": "A-P04",
    "A-DC07": "A-DOM12",
    "A-DC09": "A-AG01",
    "C-DC21": "C-DC02i",
}

# These technical IDs formalize shared relations described without numbered rows
# in the narrative inventory. Each is documented next to that prose declaration.
SPEC_ONLY_TECHNICAL_IDS = {"PROV-R1", "PROV-R2", "ID-R1"}

# Every global relation is represented by explicit module relations, a named global
# property, or a documented multi-property mechanism. Expected domains/ranges are
# checked against the listed declarations so this cannot become a blanket skip list.
GLOBAL_RELATION_BRANCHES = [
    ("D-01", {"Paper", "Repository"}, {"DatasetResource"}, {"C-P20", "C-C15"}, "mapped", "Paper and repository dataset use"),
    ("D-02", {"Repository", "Tool"}, {"Method"}, {"C-C16"}, "mapped", "Code implementation of paper methods"),
    ("D-03", {"DocumentationPage"}, {"Repository"}, {"C-DC13"}, "grouped", "documents/mirrors is the documented module realization"),
    ("D-04", {"DocumentationPage", "Paper", "Repository"}, {"Repository"}, {"C-DC14", "C-P32", "C-P33", "C-C27"}, "mapped", "Formal repository-reference property branches"),
    ("D-04", {"DatasetResource"}, {"Repository"}, {"C-D19"}, "grouped", "Dataset-origin generic references include repositories"),
    ("D-05", {"DocumentationPage", "Repository", "Paper"}, {"DatasetResource"}, {"C-DC15", "C-C19", "C-P29"}, "mapped", "All three approved dataset-reference branches"),
    ("D-06", {"DocumentationPage", "Tool", "ComputationalModel"}, {"Tool", "ComputationalModel", "Repository", "Paper", "DocumentationPage", "DatasetResource"}, {"C-DC17", "C-DC19", "C-DC15", "D-22", "D-23", "D-24", "D-25"}, "mechanism", "Product catalog aggregation uses seven named backing properties"),
    ("D-07", {"Repository", "DocumentationPage"}, {"Paper"}, {"C-C17", "C-DC26"}, "mapped", "Repository and documentation publication references"),
    ("D-08", {"Paper"}, {"Paper"}, {"C-P21"}, "mapped", "Paper citation"),
    ("D-09", {"Paper"}, {"Paper"}, {"C-P22"}, "mapped", "Corrigendum relation"),
    ("D-10", {"DatasetResource"}, {"DatasetResource"}, {"C-D12", "C-D13"}, "grouped", "Forward and inverse collection membership"),
    ("D-11", {"DatasetResource"}, {"DatasetResource"}, {"C-D14"}, "grouped", "derivedFrom carries the versionedFrom narrative alias"),
    ("D-12", {"ToolConfiguration"}, {"Tool"}, {"C-D11"}, "mapped", "Application launch relation; launchURL is a literal attribute"),
    ("D-13", {"Repository"}, {"Repository"}, {"C-C13"}, "grouped", "Repository dependency relation"),
    ("D-14", {"Repository"}, {"Repository"}, {"C-C14"}, "grouped", "Repository fork relation"),
    ("D-15", {"DocumentationPage"}, {"DocumentationPage"}, {"C-DC22"}, "mapped", "Explicit page-to-page reference"),
    ("D-16", {"owl:Thing"}, {"ComputationalModel", "Tool", "Variable", "Concept", "HydrologicFeature", "EvaluationMetric", "Parameter", "Algorithm"}, {"D-16"}, "global", "Shared-domain consolidation mechanism"),
    ("D-17", {"DatasetResource"}, {"Repository"}, {"D-17"}, "global", "Explicit generation provenance"),
    ("D-18", {"Paper"}, {"HydrologicFeature"}, {"C-P17"}, "grouped", "Paper studiesFeature branch"),
    ("D-18", {"DatasetResource"}, {"HydrologicFeature"}, {"C-D15"}, "grouped", "Dataset referencesFeature branch"),
    ("D-18", {"DocumentationPage"}, {"HydrologicFeature"}, {"C-DC23"}, "mapped", "Documentation referencesFeature branch"),
    ("D-19", {"DocumentationPage"}, {"Repository", "DocumentationPage", "Tool"}, {"C-DC18"}, "grouped", "announces is the formal realization of the announcement/reference family"),
    ("D-20", {"Repository"}, {"Identifier"}, {"C-C18"}, "mapped", "Archived snapshot identifier relation"),
    ("D-21", {"Paper"}, {"ComputationalModel"}, {"C-P23"}, "grouped", "Paper model mention"),
    ("D-21", {"DocumentationPage", "Repository", "DatasetResource"}, {"ComputationalModel"}, {"C-DC24", "C-C23", "C-D26"}, "mapped", "Documentation, repository, and dataset model mentions"),
    ("D-21", {"Paper"}, {"DatasetMention", "DatasetResource"}, {"C-P24"}, "grouped", "Paper dataset mention"),
    ("D-21", {"DocumentationPage"}, {"DatasetResource"}, {"C-DC25"}, "mapped", "Documentation dataset mention"),
    ("D-22", {"Tool", "ComputationalModel"}, {"Repository"}, {"D-22"}, "global", "Product implementation backing edge"),
    ("D-23", {"Tool", "ComputationalModel"}, {"Paper"}, {"D-23"}, "global", "Product publication backing edge"),
    ("D-24", {"DocumentationPage"}, {"Tool", "ComputationalModel", "DatasetResource", "Method"}, {"D-24", "C-DC07", "C-DC16", "C-DC27", "C-DC28"}, "mechanism", "Parent property plus four typed description subproperties"),
    ("D-25", {"Tool", "ComputationalModel", "DatasetResource", "Method"}, {"DocumentationPage"}, {"D-25"}, "global", "Inverse documentation relation"),
]


def load_spec() -> dict[str, Any]:
    """Load the machine-readable ontology specification."""
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def relation_by_id(relation_id: str) -> dict[str, Any]:
    """Return one ontology relation declaration by inventory ID."""
    matches = [item for item in load_spec()["relations"] if item["id"] == relation_id]
    if len(matches) != 1:
        raise AssertionError(f"Expected one relation {relation_id}, found {len(matches)}")
    return matches[0]


def parse_owl() -> ET.Element:
    """Parse the generated RDF/XML document and return its root."""
    return ET.parse(OWL_PATH).getroot()


def object_properties(root: ET.Element, local_name: str) -> list[ET.Element]:
    """Return generated object properties having the requested local name."""
    return [
        prop
        for prop in root.findall("owl:ObjectProperty", NS)
        if prop.get(RDF_ABOUT) in {f"#{local_name}", f"{NS['ciroh']}{local_name}"}
    ]


def entity_for_inventory_id(root: ET.Element, inventory_id: str) -> ET.Element:
    """Return the generated OWL entity carrying one inventory annotation."""
    matches = [
        entity
        for entity in root
        if inventory_id
        in {
            item.text
            for item in entity.findall("ciroh:inventoryId", NS)
            if item.text is not None
        }
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"Expected one generated entity for {inventory_id}, found {len(matches)}"
        )
    return matches[0]


def as_set(value: Any) -> set[str]:
    """Return a scalar or list specification value as a set of strings."""
    if isinstance(value, list):
        return {str(item) for item in value}
    return {str(value)}


def property_expression_members(prop: ET.Element, axis: str) -> set[str]:
    """Return local class names from a generated property domain or range."""
    def ontology_class_name(iri: str) -> str:
        """Map reused external local names back to ontology specification names."""
        local_name = iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
        return GENERATED_CLASS_LOCAL_ALIASES.get(local_name, local_name)

    element = prop.find(f"rdfs:{axis}", NS)
    if element is None:
        return set()
    direct = element.get(RDF_RESOURCE)
    if direct:
        return {ontology_class_name(direct)}
    return {
        ontology_class_name(str(item.get(RDF_ABOUT)))
        for item in element.findall("owl:Class/owl:unionOf/rdf:Description", NS)
        if item.get(RDF_ABOUT)
    }


def property_inventory_ids(prop: ET.Element) -> set[str]:
    """Return all inventory IDs annotating one generated property."""
    return {
        item.text
        for item in prop.findall("ciroh:inventoryId", NS)
        if item.text is not None
    }


def inventory_table_ids() -> set[str]:
    """Parse stable IDs appearing in the first column of inventory tables."""
    pattern = re.compile(r"^\|\s*([A-Z]+-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\s*\|")
    return {
        match.group(1)
        for line in INVENTORY_PATH.read_text(encoding="utf-8").splitlines()
        if (match := pattern.match(line))
    }


class OntologyFormalizationPatchTests(unittest.TestCase):
    """Verify the complete ontology 0.1.3 pre-pilot patch."""

    def test_spec_version_is_0_1_3(self) -> None:
        """The authoritative specification records candidate version 0.1.3."""
        self.assertEqual(load_spec()["ontology"]["version"], "0.1.3")

    def test_c_p29_declaration(self) -> None:
        """C-P29 realizes the Paper-domain branch of global D-05."""
        relation = relation_by_id("C-P29")
        self.assertEqual(relation["name"], "referencesDataset")
        self.assertEqual(relation["domain"], "Paper")
        self.assertEqual(relation["range"], "DatasetResource")
        self.assertEqual(relation["maps_to"], "D-05")
        self.assertEqual(relation["anchor"], "cito:citesAsDataSource")
        self.assertEqual(relation["alt_anchor"], "dcterms:references")
        self.assertTrue(relation["consol"])

    def test_generated_version_is_0_1_3(self) -> None:
        """The generated ontology records the patched semantic version."""
        version = parse_owl().find("owl:Ontology/owl:versionInfo", NS)
        self.assertIsNotNone(version)
        self.assertEqual(version.text, "0.1.3")

    def test_c_p08_is_hypothesis_testing_only(self) -> None:
        """C-P08 excludes theoretical grounding while retaining its testedBy range."""
        relation = relation_by_id("C-P08")
        self.assertEqual(relation["name"], "testedBy")
        self.assertEqual(as_set(relation["domain"]), {"Hypothesis"})
        self.assertNotIn("TheoreticalBasis", as_set(relation["domain"]))
        self.assertEqual(as_set(relation["range"]), {"Method", "Experiment"})

        prop = object_properties(parse_owl(), "testedBy")[0]
        self.assertEqual(property_inventory_ids(prop), {"C-P08"})
        self.assertEqual(property_expression_members(prop, "domain"), {"Hypothesis"})
        self.assertEqual(property_expression_members(prop, "range"), {"Method", "Experiment"})

    def test_c_p12_retains_only_limitation_semantics(self) -> None:
        """C-P12 keeps its signature and no longer claims a summary branch."""
        relation = relation_by_id("C-P12")
        self.assertEqual(relation["name"], "hasLimitation")
        self.assertEqual(as_set(relation["domain"]), {"Paper", "Finding"})
        self.assertEqual(as_set(relation["range"]), {"Limitation"})
        self.assertNotRegex(relation.get("note", "").casefold(), r"summar(?:y|ize|izes)")

    def test_c_p09_retains_positive_support_signature(self) -> None:
        """C-P09 remains structurally unchanged without undeclared aliases."""
        relation = relation_by_id("C-P09")
        self.assertEqual(relation["name"], "supports")
        self.assertEqual(as_set(relation["domain"]), {"Finding", "Claim"})
        self.assertEqual(as_set(relation["range"]), {"Claim", "Conclusion"})
        note = relation.get("note", "").casefold()
        for undeclared_alias in ("notsupports", "refutes", "contradicts", "argues"):
            self.assertNotIn(undeclared_alias, note)

    def test_c_dc15_remains_documentation_page_relation(self) -> None:
        """The existing documentation realization remains unchanged."""
        relation = relation_by_id("C-DC15")
        self.assertEqual(relation["name"], "referencesDataset")
        self.assertEqual(relation["domain"], "DocumentationPage")
        self.assertEqual(relation["range"], "DatasetResource")
        self.assertEqual(relation["maps_to"], "D-05")

    def test_c_c19_completes_repository_d05_branch(self) -> None:
        """C-C19 realizes the Repository-domain branch without claiming use."""
        relation = relation_by_id("C-C19")
        self.assertEqual(relation["name"], "referencesDataset")
        self.assertEqual(relation["domain"], "Repository")
        self.assertEqual(relation["range"], "DatasetResource")
        self.assertEqual(relation["anchor"], "dcterms:references")
        self.assertEqual(relation["maps_to"], "D-05")
        self.assertTrue(relation["consol"])

    def test_repository_use_and_reference_relations_are_distinct(self) -> None:
        """C-C15 use semantics remain separate from C-C19 references."""
        uses_dataset = relation_by_id("C-C15")
        references_dataset = relation_by_id("C-C19")
        self.assertEqual(uses_dataset["name"], "usesDataset")
        self.assertEqual(references_dataset["name"], "referencesDataset")
        self.assertEqual(uses_dataset["domain"], references_dataset["domain"])
        self.assertEqual(uses_dataset["range"], references_dataset["range"])
        self.assertEqual(uses_dataset["maps_to"], "D-01")
        self.assertEqual(references_dataset["maps_to"], "D-05")

    def test_c_d19_is_not_d05_realization(self) -> None:
        """Dataset-origin generic references no longer claim D-05."""
        relation = relation_by_id("C-D19")
        self.assertEqual(relation["name"], "references")
        self.assertEqual(relation["domain"], "DatasetResource")
        self.assertEqual(relation["anchor"], "dcterms:references")
        self.assertNotIn("alt_anchor", relation)
        self.assertNotIn("maps_to", relation)
        self.assertNotIn("paper->dataset", relation.get("note", "").casefold())

    def test_paper_dataset_relations_remain_distinct(self) -> None:
        """Use, mention, and bibliographic reference retain separate rules."""
        relations = {item["id"]: item for item in load_spec()["relations"]}
        self.assertEqual(relations["C-P20"]["name"], "usesDataset")
        self.assertEqual(relations["C-P24"]["name"], "mentionsDataset")
        self.assertEqual(relations["C-P29"]["name"], "referencesDataset")
        self.assertEqual(
            {relations[item]["name"] for item in ("C-P20", "C-P24", "C-P29")},
            {"usesDataset", "mentionsDataset", "referencesDataset"},
        )

    def test_generated_references_dataset_property_is_merged(self) -> None:
        """All three module rules generate one formal object property."""
        properties = object_properties(parse_owl(), "referencesDataset")
        self.assertEqual(len(properties), 1)
        prop = properties[0]

        inventory_ids = {
            item.text
            for item in prop.findall("ciroh:inventoryId", NS)
            if item.text is not None
        }
        self.assertEqual(inventory_ids, {"C-P29", "C-DC15", "C-C19"})

        domains = {
            item.get(RDF_ABOUT)
            for item in prop.findall("rdfs:domain/owl:Class/owl:unionOf/rdf:Description", NS)
        }
        self.assertEqual(domains, {"#Paper", "#DocumentationPage", "#Repository"})

        range_element = prop.find("rdfs:range", NS)
        self.assertIsNotNone(range_element)
        self.assertEqual(range_element.get(f"{{{NS['rdf']}}}resource"), "#DatasetResource")

        comments = [item.text or "" for item in prop.findall("rdfs:comment", NS)]
        self.assertIn("Maps to inventory relation: D-05", comments)
        reuse_anchors = {
            item.text
            for item in prop.findall("ciroh:reuseAnchor", NS)
            if item.text is not None
        }
        self.assertEqual(
            reuse_anchors,
            {"cito:citesAsDataSource", "dcterms:references", "ciroh:"},
        )

    def test_generated_generic_references_has_no_d05_trace(self) -> None:
        """The separate DatasetResource-origin property has no D-05 mapping."""
        properties = object_properties(parse_owl(), "references")
        self.assertEqual(len(properties), 1)
        prop = properties[0]
        comments = [item.text or "" for item in prop.findall("rdfs:comment", NS)]
        self.assertNotIn("Maps to inventory relation: D-05", comments)
        reuse_anchors = {
            item.text
            for item in prop.findall("ciroh:reuseAnchor", NS)
            if item.text is not None
        }
        self.assertEqual(reuse_anchors, {"dcterms:references"})

    def test_generated_object_property_count_is_90(self) -> None:
        """Twenty declarations add exactly seven distinct object properties."""
        self.assertEqual(len(parse_owl().findall("owl:ObjectProperty", NS)), 90)

    def test_has_sub_page_machine_id_and_narrative_alias(self) -> None:
        """C-DC02i remains formal while C-DC21 is comment-only traceability."""
        spec = load_spec()
        relation_ids = {relation["id"] for relation in spec["relations"]}
        self.assertIn("C-DC02i", relation_ids)
        self.assertNotIn("C-DC21", relation_ids)
        relation = relation_by_id("C-DC02i")
        self.assertEqual(relation["name"], "hasSubPage")
        self.assertEqual(relation["domain"], "DocumentationPage")
        self.assertEqual(relation["range"], "DocumentationPage")
        self.assertEqual(relation["inverse_of"], "isPartOf")

        prop = object_properties(parse_owl(), "hasSubPage")[0]
        self.assertEqual(property_inventory_ids(prop), {"C-DC02i"})
        comments = [item.text or "" for item in prop.findall("rdfs:comment", NS)]
        self.assertTrue(any("narrative inventory alias: C-DC21" in item for item in comments))

    def test_frozen_hub_hierarchy_edges_keep_c_dc02i(self) -> None:
        """The frozen Hub graph retains its established hasSubPage inventory ID."""
        if not HUB_OUTPUT_PATH.exists():
            self.skipTest("Frozen CIROH Hub output is not available")
        output = json.loads(HUB_OUTPUT_PATH.read_text(encoding="utf-8"))
        edges = [edge for edge in output["edges"] if edge["relation"] == "hasSubPage"]
        self.assertGreater(len(edges), 0)
        self.assertEqual({edge["inventoryId"] for edge in edges}, {"C-DC02i"})
        self.assertFalse(any(edge["inventoryId"] == "C-DC21" for edge in output["edges"]))

    def test_new_documentation_module_declarations(self) -> None:
        """The four missing DocumentationPage branches map to their global rules."""
        expected = {
            "C-DC22": ("references", "DocumentationPage", "DocumentationPage", "D-15"),
            "C-DC23": ("referencesFeature", "DocumentationPage", "HydrologicFeature", "D-18"),
            "C-DC24": ("mentionsModel", "DocumentationPage", "ComputationalModel", "D-21"),
            "C-DC25": ("mentionsDataset", "DocumentationPage", "DatasetResource", "D-21"),
        }
        for inventory_id, declaration in expected.items():
            with self.subTest(inventory_id=inventory_id):
                relation = relation_by_id(inventory_id)
                self.assertEqual(
                    (relation["name"], relation["domain"], relation["range"], relation["maps_to"]),
                    declaration,
                )

    def test_announces_and_nearby_semantics_remain_distinct(self) -> None:
        """Announcements, references, descriptions, mentions, and uses stay separate."""
        relations = {relation["id"]: relation for relation in load_spec()["relations"]}
        self.assertEqual(relations["C-DC18"]["name"], "announces")
        self.assertEqual(relations["C-D18"]["name"], "usesTool")
        self.assertNotEqual(relations["C-DC18"]["name"], relations["C-DC22"]["name"])
        self.assertNotEqual(relations["C-DC16"]["name"], relations["C-DC24"]["name"])
        self.assertNotEqual(relations["C-DC15"]["name"], relations["C-DC25"]["name"])
        self.assertEqual(len(object_properties(parse_owl(), "announces")), 1)
        self.assertEqual(len(object_properties(parse_owl(), "references")), 1)

    def test_new_relations_merge_into_expected_properties(self) -> None:
        """Merged domains, ranges, and traceability match the approved declarations."""
        expected = {
            "references": (
                {"DatasetResource", "DocumentationPage"},
                {"Paper", "Repository", "DatasetResource", "DocumentationPage"},
                {"C-D19", "C-DC22"},
            ),
            "referencesFeature": (
                {"DatasetResource", "DocumentationPage"},
                {"HydrologicFeature"},
                {"C-D15", "C-DC23"},
            ),
            "mentionsModel": (
                {"Paper", "DocumentationPage", "DatasetResource", "Repository"},
                {"ComputationalModel"},
                {"C-P23", "C-DC24", "C-D26", "C-C23"},
            ),
            "mentionsDataset": (
                {"Paper", "DocumentationPage"},
                {"DatasetMention", "DatasetResource"},
                {"C-P24", "C-DC25"},
            ),
        }
        for name, (domains, ranges, inventory_ids) in expected.items():
            with self.subTest(property=name):
                properties = object_properties(parse_owl(), name)
                self.assertEqual(len(properties), 1)
                self.assertEqual(property_expression_members(properties[0], "domain"), domains)
                self.assertEqual(property_expression_members(properties[0], "range"), ranges)
                self.assertEqual(property_inventory_ids(properties[0]), inventory_ids)

    def test_source_relation_declaration_count_is_125(self) -> None:
        """The patch adds twenty declarations without changing classes."""
        spec = load_spec()
        self.assertEqual(len(spec["classes"]), 75)
        self.assertEqual(len(spec["relations"]), 125)
        all_ids = [entry["id"] for section in ("classes", "relations") for entry in spec[section]]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_corrected_and_new_property_signatures(self) -> None:
        """Corrected collapsed declarations generate the approved signatures."""
        expected = {
            "usesTool": ({"Paper", "DatasetResource", "Repository"}, {"Tool"}, {"C-P15", "C-D18", "C-C11"}),
            "mentionsTool": ({"Paper", "DatasetResource", "Repository"}, {"Tool"}, {"C-P31", "C-D24", "C-C22"}),
            "usesModel": ({"Paper", "Method", "DatasetResource", "Repository"}, {"ComputationalModel"}, {"C-P13", "C-D25", "C-C21"}),
            "mentionsModel": ({"Paper", "DocumentationPage", "DatasetResource", "Repository"}, {"ComputationalModel"}, {"C-P23", "C-DC24", "C-D26", "C-C23"}),
            "mentionsVariable": ({"Paper", "DataDescription", "Repository"}, {"Variable"}, {"C-P16", "C-C12"}),
            "mentionsConcept": ({"Paper", "DatasetResource", "Repository", "DocumentationPage"}, {"Concept"}, {"C-P30", "C-D23", "C-C26", "C-DC08"}),
            "explainsWorkflow": ({"DocumentationPage", "Procedure", "Repository", "DatasetResource"}, {"Workflow"}, {"C-DC09", "C-C10", "C-D22"}),
            "referencesRepository": ({"DocumentationPage", "Paper", "Repository"}, {"Repository"}, {"C-DC14", "C-P32", "C-C27"}),
            "referencePublication": ({"Repository", "DocumentationPage"}, {"Paper"}, {"C-C17", "C-DC26"}),
            "describes": ({"DocumentationPage"}, {"Tool", "ComputationalModel", "DatasetResource", "Method"}, {"D-24"}),
            "documentedBy": ({"Tool", "ComputationalModel", "DatasetResource", "Method"}, {"DocumentationPage"}, {"D-25"}),
        }
        for name, (domains, ranges, inventory_ids) in expected.items():
            with self.subTest(property=name):
                prop = object_properties(parse_owl(), name)
                self.assertEqual(len(prop), 1)
                self.assertEqual(property_expression_members(prop[0], "domain"), domains)
                self.assertEqual(property_expression_members(prop[0], "range"), ranges)
                self.assertEqual(property_inventory_ids(prop[0]), inventory_ids)

    def test_use_mention_and_split_semantics_are_distinct(self) -> None:
        """Use, mention, function, algorithm, variable, and parameter remain distinct."""
        relations = {item["id"]: item for item in load_spec()["relations"]}
        self.assertNotEqual(relations["C-P15"]["name"], relations["C-P31"]["name"])
        self.assertNotEqual(relations["C-P13"]["name"], relations["C-P23"]["name"])
        self.assertNotEqual(relations["C-C24"]["name"], relations["C-C25"]["name"])
        self.assertNotEqual(relations["C-C08"]["name"], relations["C-C20"]["name"])
        self.assertEqual(as_set(relations["C-C12"]["range"]), {"Variable"})
        self.assertNotIn("Parameter", as_set(relations["C-C12"]["range"]))

    def test_repository_model_use_is_not_implementation(self) -> None:
        """C-C21 use evidence stays distinct from D-22 implementation evidence."""
        uses_model = relation_by_id("C-C21")
        implemented_by = relation_by_id("D-22")
        use_evidence = uses_model["evidence"].casefold()
        implementation_evidence = implemented_by["evidence"].casefold()

        self.assertNotIn("implementation", use_evidence)
        self.assertNotIn("implements", use_evidence)
        for required in ("use", "execution", "configuration", "dependency", "workflow"):
            self.assertIn(required, use_evidence)
        self.assertEqual(as_set(implemented_by["domain"]), {"Tool", "ComputationalModel"})
        self.assertEqual(as_set(implemented_by["range"]), {"Repository"})
        for required in ("product-card", "doccardlist", "readme", "citation", "implements"):
            self.assertIn(required, implementation_evidence)

    def test_approved_subproperties_and_inverse_are_generated(self) -> None:
        """Typed specializations and the broadened inverse survive serialization."""
        expected_subproperties = {
            "hasCodeRepository": "referencesRepository",
            "describesDataset": "describes",
            "describesMethod": "describes",
        }
        for child, parent in expected_subproperties.items():
            with self.subTest(child=child):
                prop = object_properties(parse_owl(), child)[0]
                subproperty = prop.find("rdfs:subPropertyOf", NS)
                self.assertIsNotNone(subproperty)
                self.assertEqual(subproperty.get(RDF_RESOURCE), f"#{parent}")
        documented_by = object_properties(parse_owl(), "documentedBy")[0]
        inverse = documented_by.find("owl:inverseOf", NS)
        self.assertIsNotNone(inverse)
        self.assertEqual(inverse.get(RDF_RESOURCE), "#describes")

    def test_frozen_phase_b_outputs_are_unchanged_and_resolve(self) -> None:
        """Frozen 0.1.1 graphs remain byte-identical and compatible with 0.1.3."""
        spec = load_spec()
        classes = {item["id"]: item["name"] for item in spec["classes"]}
        relations = {item["id"]: item["name"] for item in spec["relations"]}
        for path, expected_hash in FROZEN_OUTPUT_HASHES.items():
            with self.subTest(path=path):
                self.assertTrue(path.exists())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected_hash)
                output = json.loads(path.read_text(encoding="utf-8"))
                for node in output["nodes"]:
                    pair = (node["inventoryId"], node["class"])
                    if classes.get(pair[0]) == pair[1]:
                        continue
                    self.assertIn(pair, FROZEN_NODE_COMPATIBILITY)
                    self.assertIn(FROZEN_NODE_COMPATIBILITY[pair], classes)
                for edge in output["edges"]:
                    pair = (edge["inventoryId"], edge["relation"])
                    if relations.get(pair[0]) == pair[1]:
                        continue
                    self.assertIn(pair, FROZEN_EDGE_COMPATIBILITY)
                    self.assertIn(FROZEN_EDGE_COMPATIBILITY[pair], relations)

    def test_corrected_llm_ids_have_no_frozen_edges(self) -> None:
        """The four corrected declarations were unused by deterministic Phase B."""
        corrected_ids = {"C-C08", "C-C11", "C-C12", "C-D18"}
        for path in FROZEN_OUTPUT_HASHES:
            output = json.loads(path.read_text(encoding="utf-8"))
            hits = [edge for edge in output["edges"] if edge["inventoryId"] in corrected_ids]
            self.assertEqual(hits, [], str(path))

    def test_c_p08_has_no_frozen_edges(self) -> None:
        """The narrowed C-P08 declaration requires no frozen ABox migration."""
        for path in FROZEN_OUTPUT_HASHES:
            output = json.loads(path.read_text(encoding="utf-8"))
            hits = [
                edge
                for edge in output["edges"]
                if edge["inventoryId"] == "C-P08" or edge["relation"] == "testedBy"
            ]
            self.assertEqual(hits, [], str(path))

    def test_inventory_yaml_reconciliation_has_no_unexplained_mismatch(self) -> None:
        """Narrative IDs reconcile exactly, by approved alias, or by documented role."""
        spec = load_spec()
        yaml_ids = {
            entry["id"]
            for section in ("classes", "relations")
            for entry in spec[section]
        }
        inventory_ids = inventory_table_ids()
        inventory_text = INVENTORY_PATH.read_text(encoding="utf-8")

        for alias, canonical in APPROVED_INVENTORY_ALIASES.items():
            with self.subTest(alias=alias):
                self.assertIn(alias, inventory_text)
                self.assertIn(canonical, yaml_ids)
        self.assertEqual(APPROVED_INVENTORY_ALIASES["A-DC04"], "A-P04")
        self.assertEqual(APPROVED_INVENTORY_ALIASES["C-DC21"], "C-DC02i")

        nonformal_inventory_ids = {
            inventory_id
            for inventory_id in inventory_ids
            if inventory_id.startswith(("B-", "D-", "E-"))
        }
        unexplained_inventory_ids = (
            inventory_ids
            - yaml_ids
            - set(APPROVED_INVENTORY_ALIASES)
            - nonformal_inventory_ids
        )
        unexplained_yaml_ids = (
            yaml_ids
            - inventory_ids
            - set(APPROVED_INVENTORY_ALIASES.values())
            - SPEC_ONLY_TECHNICAL_IDS
        )
        self.assertEqual(unexplained_inventory_ids, set())
        self.assertEqual(unexplained_yaml_ids, set())
        for technical_id in SPEC_ONLY_TECHNICAL_IDS:
            self.assertIn(technical_id, inventory_text)

    def test_global_relation_branches_have_no_unexplained_gap(self) -> None:
        """Every D-01 through D-25 branch has a checked formal realization."""
        relations = {relation["id"]: relation for relation in load_spec()["relations"]}
        audited_globals = {entry[0] for entry in GLOBAL_RELATION_BRANCHES}
        self.assertEqual(audited_globals, {f"D-{index:02d}" for index in range(1, 26)})

        for global_id, domains, ranges, relation_ids, mode, rationale in GLOBAL_RELATION_BRANCHES:
            with self.subTest(global_id=global_id, domains=sorted(domains), mode=mode):
                self.assertTrue(rationale.strip())
                self.assertIn(mode, {"mapped", "grouped", "mechanism", "global"})
                declarations = [relations[relation_id] for relation_id in relation_ids]
                covered_domains = set().union(*(as_set(item["domain"]) for item in declarations))
                covered_ranges = set().union(*(as_set(item["range"]) for item in declarations))
                self.assertTrue(domains <= covered_domains, (global_id, domains, covered_domains))
                self.assertTrue(ranges <= covered_ranges, (global_id, ranges, covered_ranges))
                if mode == "mapped":
                    self.assertTrue(
                        all(item.get("maps_to") == global_id for item in declarations),
                        (global_id, relation_ids),
                    )
                elif mode == "global":
                    self.assertEqual(relation_ids, {global_id})

    def test_all_alternative_anchors_are_serialized(self) -> None:
        """Every class and relation alt_anchor is preserved as an annotation."""
        spec = load_spec()
        root = parse_owl()
        entries = [
            item
            for section in ("classes", "relations")
            for item in spec[section]
            if item.get("alt_anchor")
        ]
        self.assertGreater(len(entries), 0)
        for entry in entries:
            with self.subTest(inventory_id=entry["id"]):
                entity = entity_for_inventory_id(root, entry["id"])
                anchors = {
                    item.text
                    for item in entity.findall("ciroh:reuseAnchor", NS)
                    if item.text is not None
                }
                self.assertIn(entry["alt_anchor"], anchors)
                comments = [item.text or "" for item in entity.findall("rdfs:comment", NS)]
                self.assertIn(
                    f"Alternative reuse anchor: {entry['alt_anchor']}",
                    comments,
                )

    @unittest.skipUnless(importlib.util.find_spec("owlready2"), "owlready2 is required")
    def test_ontology_build_is_byte_deterministic(self) -> None:
        """Three independent Python processes serialize identical ontology bytes."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            first = Path(temporary_directory) / "first.owl"
            second = Path(temporary_directory) / "second.owl"
            third = Path(temporary_directory) / "third.owl"
            for output in (first, second, third):
                script = (
                    "from pathlib import Path; "
                    "from src.ontology.build_ontology import build_ontology; "
                    f"build_ontology(output_path=Path({str(output)!r}))"
                )
                subprocess.run(
                    [sys.executable, "-c", script],
                    cwd=PROJECT_ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), third.read_bytes())
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(third.read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
