"""Focused and frozen-corpus tests for publication preprocessing Phase A."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from openpyxl import Workbook
import yaml

from src.preprocessing import build_publication_corpus as publication


FROZEN_RAW = publication.PROJECT_ROOT / "data/raw/papers"
FROZEN_OVERRIDES = publication.PROJECT_ROOT / "data/curation/papers/publication_curation_overrides.yaml"


class PublicationFixture:
    """Build small authoritative publication inputs in a temporary directory."""

    def __init__(self, root: Path) -> None:
        """Initialize standard raw and override paths."""

        self.raw = root / "raw" / "papers"
        self.raw.mkdir(parents=True)
        self.overrides = root / "curation" / "publication_curation_overrides.yaml"
        self.overrides.parent.mkdir(parents=True)

    def write_excel(self, rows: list[dict[str, object]]) -> None:
        """Write the authoritative workbook with its required columns."""

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(list(publication.REQUIRED_EXCEL_COLUMNS))
        for row in rows:
            sheet.append([row.get(column) for column in publication.REQUIRED_EXCEL_COLUMNS])
        workbook.save(self.raw / publication.EXCEL_FILE)

    def write_bibtex(self, entries: list[dict[str, object]]) -> None:
        """Write deterministic BibTeX records, including keys containing spaces."""

        blocks: list[str] = []
        for entry in entries:
            fields = entry["fields"]
            lines = [f"@{entry.get('type', 'article')}{{{entry['key']},"]
            for key, value in fields.items():
                lines.append(f"  {key} = {{{value}}},")
            lines.append("}")
            blocks.append("\n".join(lines))
        (self.raw / publication.BIBTEX_FILE).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")

    def write_overrides(self, records: dict[str, object] | None = None) -> None:
        """Write the stable declarative override schema."""

        self.overrides.write_text(
            yaml.safe_dump({"schema_version": "1.1.0", "records": records or {}}, sort_keys=False),
            encoding="utf-8",
        )

    def write_artifacts(self, local_id: str, markdown: str = "# Paper\n") -> None:
        """Write all seven required file forms for one synthetic publication."""

        (self.raw / "pdfs").mkdir(exist_ok=True)
        (self.raw / "pdfs" / f"{local_id}.pdf").write_bytes(b"%PDF-1.4\n")
        base = self.raw / "markdowns" / local_id
        (base / "markdown").mkdir(parents=True)
        (base / "chunks").mkdir()
        (base / "json").mkdir()
        (base / "markdown" / f"{local_id}_md.md").write_text(markdown, encoding="utf-8", newline="")
        metadata = {"page_stats": [{"page": 1}], "table_of_contents": [{"title": "Paper"}]}
        for path, value in (
            (base / "markdown" / f"{local_id}_md_meta.json", metadata),
            (base / "chunks" / f"{local_id}_chunks.json", {"chunks": []}),
            (base / "chunks" / f"{local_id}_chunks_meta.json", {"count": 0}),
            (base / "json" / f"{local_id}_json.json", {"children": []}),
            (base / "json" / f"{local_id}_json_meta.json", {"version": 1}),
        ):
            path.write_text(json.dumps(value), encoding="utf-8")


class PublicationPhaseAUnitTests(unittest.TestCase):
    """Exercise identity, reconciliation, extraction, validation, and determinism."""

    def test_identity_precedence_encoding_repair_and_markdown_extraction(self) -> None:
        """Excel identity wins while safe key repair and controlled sections remain mechanical."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            repaired_key = "Ramírez_2024"
            mojibake_key = repaired_key.encode("utf-8").decode("mac_roman")
            fixture.write_excel(
                [
                    {
                        "id": 1,
                        "ZoteroID": "Author With Space_2024",
                        "title": "Excel title",
                        "year": 2024,
                        "doi": "HTTPS://DOI.ORG/10.1234/EXAMPLE",
                        "url": "https://example.org/article",
                        "journal": "Curated Journal",
                    },
                    {
                        "id": 2,
                        "ZoteroID": mojibake_key,
                        "title": "URL publication",
                        "year": 2023,
                        "doi": None,
                        "url": "https://example.org/url-only",
                        "journal": "Proceedings",
                    },
                ]
            )
            fixture.write_bibtex(
                [
                    {
                        "key": "Author With Space_2024",
                        "fields": {
                            "title": "Different Bib title",
                            "author": "Doe, Jane and van Rossum, Guido",
                            "year": "2024",
                            "journal": "Curated Journal",
                            "doi": "10.1234/example",
                            "keywords": "River Ice; Floods",
                        },
                    },
                    {
                        "key": repaired_key,
                        "type": "inproceedings",
                        "fields": {
                            "title": "URL publication",
                            "author": "Ramírez, Ana",
                            "year": "2023",
                            "booktitle": "Proceedings",
                            "url": "https://example.org/url-only",
                        },
                    },
                ]
            )
            fixture.write_overrides()
            fixture.write_artifacts(
                "1",
                "# Excel title\r\n## Introduction\r\n"
                "THIS_FULL_BODY_TEXT_MUST_NOT_BE_EMBEDDED_IN_PHASE_A_JSON\r\n"
                "## 1 Abstract\r\nMeasured abstract.\r\n"
                "## Keywords\r\nHydrology, Streamflow\r\n## References\r\n"
                "Doe (2020). https://doi.org/10.5555/REF.1\r\n"
                "## Data and Code Availability\r\nData: https://data.example/item and doi:10.7777/DATA.2\r\n",
            )
            fixture.write_artifacts("2")

            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            validation = publication.validate_corpus(corpus, fixture.raw, 2)
            self.assertTrue(validation["valid"], validation["issues"])
            first, second = corpus["publications"]
            self.assertEqual(first["canonical_artifact_id"], "https://doi.org/10.1234/example")
            self.assertEqual([item["scheme"] for item in first["identifiers"]], ["doi", "url"])
            self.assertEqual(first["bibliographic"]["title"], "Excel title")
            self.assertEqual(first["bibliographic"]["abstract"], "Measured abstract.")
            self.assertEqual(
                set(first["content"]),
                {"headings", "explicit_keywords", "reference_dois", "availability_identifiers"},
            )
            self.assertEqual(
                [heading["normalized_text"] for heading in first["content"]["headings"]],
                ["excel title", "introduction", "abstract", "keywords", "references", "data and code availability"],
            )
            self.assertEqual([item["value"] for item in first["content"]["explicit_keywords"]], ["hydrology", "streamflow", "river ice", "floods"])
            self.assertEqual(first["content"]["reference_dois"][0]["doi"], "10.5555/ref.1")
            self.assertEqual(
                [(item["identifier_scheme"], item["identifier_value"]) for item in first["content"]["availability_identifiers"]],
                [("url", "https://data.example/item"), ("doi", "10.7777/data.2")],
            )
            self.assertEqual(first["bibliographic"]["authors"][0]["display_name"], "Jane Doe")
            self.assertEqual(second["canonical_identifier"]["scheme"], "url")
            self.assertEqual(second["reconciliation"]["bibtex_match_method"], "reversible_encoding_repair")
            self.assertEqual(second["reconciliation"]["zotero_key_original"], mojibake_key)
            self.assertEqual(second["reconciliation"]["bibtex_key"], repaired_key)
            self.assertEqual(first["source_files"]["markdown_path"], "papers/markdowns/1/markdown/1_md.md")
            self.assertFalse(Path(first["source_files"]["markdown_path"]).is_absolute())
            serialized = publication.serialize_corpus(corpus)
            self.assertNotIn(b"THIS_FULL_BODY_TEXT_MUST_NOT_BE_EMBEDDED_IN_PHASE_A_JSON", serialized)

    def test_validation_rejects_embedded_markdown_content_field(self) -> None:
        """The Phase A 1.1 schema rejects reintroduction of complete Markdown text."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel([{"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"}])
            fixture.write_bibtex([{"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one"}}])
            fixture.write_overrides()
            fixture.write_artifacts("1", "# One\nBody text.\n")
            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            corpus["publications"][0]["content"]["markdown"] = "Body text."
            validation = publication.validate_corpus(corpus, fixture.raw, 1)
            self.assertFalse(validation["valid"])
            self.assertIn("1: content keys differ", validation["issues"])

    def test_destination_first_strict_reference_doi_extraction(self) -> None:
        """Reference parsing prefers destinations, validates strictly, and deduplicates."""

        markdown = (
            "# Body\nOutside 10.9999/not-a-reference\n"
            "## References\n"
            "Bare 10.1234/bare.\n"
            "Resolver https://doi.org/10.2345/Resolver.\n"
            "Fragment [https://doi.org/10.1175/](https://doi.org/10.1175/JHM-D-14-0147.1)\n"
            "Parentheses https://doi.org/10.1061/(ASCE)0887-381X(2009)23:1(1).\n"
            "Duplicate [10.3456/DUP](https://doi.org/10.3456/DUP)\n"
            "Autolink <https://doi.org/10.4567/AUTO>.\n"
            "Contaminated 10.1016/j.coldregions.2](https://doi.org/10.1016/j.coldregions.2017.06.011)\n"
        )
        headings = publication.extract_headings(markdown)
        records = publication.extract_reference_dois(markdown, headings, "https://doi.org/10.1111/source")
        values = [record["doi"] for record in records]
        self.assertEqual(
            values,
            [
                "10.1234/bare",
                "10.2345/resolver",
                "10.1175/jhm-d-14-0147.1",
                "10.1061/(asce)0887-381x(2009)23:1(1)",
                "10.3456/dup",
                "10.4567/auto",
                "10.1016/j.coldregions.2017.06.011",
            ],
        )
        self.assertNotIn("10.9999/not-a-reference", values)
        self.assertNotIn("10.1175/", values)
        self.assertEqual(values.count("10.3456/dup"), 1)
        self.assertEqual(len(records[4]["occurrences"]), 1)
        self.assertTrue(all(publication.normalize_extracted_doi(value) == value for value in values))

    def test_split_doi_recovery_is_source_bounded_and_conservative(self) -> None:
        """Formatting splits repair locally while prose and neighboring references stay separate."""

        cases = {
            "Normal 10.1234/valid.": ["10.1234/valid"],
            "Resolver https://doi.org/10.1234/resolver.": ["10.1234/resolver"],
            "Split https://doi.org/10.1016/j. jhydrol.2004.09.004.": [
                "10.1016/j.jhydrol.2004.09.004"
            ],
            "Line https://doi.org/10.5281/ze\nnodo.839854.": ["10.5281/zenodo.839854"],
            "Balanced https://doi.org/10.1061/(ASCE)0887-381X(2009) 23:1(1).": [
                "10.1061/(asce)0887-381x(2009)23:1(1)"
            ],
            "Two 10.1234/first; 10.5678/second.": ["10.1234/first", "10.5678/second"],
            "Prose 10.1234/short 2024 study": ["10.1234/short"],
        }
        for source, expected in cases.items():
            self.assertEqual(publication.extract_dois_from_text(source), expected, source)
        linked = "[10.1175/](https://doi.org/10.1175/JHM-D-14-0147.1)"
        self.assertEqual(publication.extract_dois_from_text(linked), ["10.1175/jhm-d-14-0147.1"])

    def test_malformed_split_doi_is_rejected_without_minimum_length_rule(self) -> None:
        """Invalid continuations are auditable while valid short DOI suffixes remain valid."""

        malformed = "https://doi.org/10.1175/1520-0493(2004) 132<2358:EOCRAT>2.0.CO;2"
        identifiers, diagnostics = publication.extract_text_identifiers_with_diagnostics(malformed)
        self.assertFalse([item for item in identifiers if item[1] == "doi"])
        self.assertEqual(diagnostics[0]["reason"], "invalid_split_doi_continuation")
        self.assertTrue(publication.is_malformed_doi_fragment("10.1175/1520-0493(2004)", malformed))
        contaminated = "10.7777/bad](not-a-valid-destination)"
        identifiers, diagnostics = publication.extract_text_identifiers_with_diagnostics(contaminated)
        self.assertFalse(identifiers)
        self.assertEqual(diagnostics[0]["reason"], "markdown_contamination")
        self.assertEqual(diagnostics[0]["candidate"], contaminated)
        for valid in ("10.1234/a", "10.1234/xy", "10.1234/abc"):
            self.assertEqual(publication.normalize_extracted_doi(valid), valid)
            self.assertFalse(publication.is_malformed_doi_fragment(valid, valid))

    def test_same_occurrence_failed_continuation_defers_accepted_prefix(self) -> None:
        """A visible prefix cannot survive its malformed Markdown destination continuation."""

        evidence = (
            r"Citation [https://doi.org/10.7777/\(base\)]"
            r"(https://doi.org/10.7777/(base)123(1993)1:2(3) "
            r"[123\(1993\)1:2\(3.](https://doi.org/10.7777/(base)123(1993)1:2(3)"
        )
        markdown = f"# References\n{evidence}\n"
        records, warnings = publication.extract_reference_dois_with_warnings(
            markdown,
            publication.extract_headings(markdown),
            "https://doi.org/10.9999/source",
        )
        self.assertNotIn("10.7777/(base)", {item["doi"] for item in records})
        deferred = next(
            item for item in warnings
            if item["category"] == "deferred_reference_doi_candidate"
        )
        self.assertEqual(deferred["detail"]["candidate"], "10.7777/(base)")
        self.assertEqual(deferred["detail"]["evidence_text"], evidence)
        self.assertEqual(deferred["detail"]["source_artifact"], "https://doi.org/10.9999/source")
        self.assertEqual(deferred["detail"]["source_location"]["line_start"], 2)
        self.assertIn("invalid_split_doi_continuation", deferred["detail"]["reason"])

    def test_independent_authoritative_short_doi_survives_other_occurrence_contradiction(self) -> None:
        """An exact autolink remains accepted when a separate malformed construct shares its prefix."""

        malformed = (
            r"Broken [https://doi.org/10.7777/\(base\)]"
            r"(https://doi.org/10.7777/(base)123(1993)1:2(3) "
            r"[123\(1993\)1:2\(3.](https://doi.org/10.7777/(base)123(1993)1:2(3)"
        )
        markdown = "# References\n<https://doi.org/10.7777/(base)>\n" + malformed + "\n"
        records, warnings = publication.extract_reference_dois_with_warnings(
            markdown,
            publication.extract_headings(markdown),
            "https://doi.org/10.9999/source",
        )
        base = next(item for item in records if item["doi"] == "10.7777/(base)")
        self.assertEqual(base["source_location"]["line_start"], 2)
        self.assertTrue(
            any(
                item["category"] == "deferred_reference_doi_candidate"
                and item["detail"]["candidate"] == "10.7777/(base)"
                and item["detail"]["source_location"]["line_start"] == 3
                for item in warnings
            )
        )

    def test_reference_split_recovery_does_not_cross_reference_boundaries(self) -> None:
        """A DOI split repairs, while a new list item cannot complete a malformed stem."""

        markdown = (
            "# References\n"
            "- First https://doi.org/10.5194/he\n"
            "ss-6-883-2002.\n"
            "- Second https://doi.org/10.1111/j\n"
            "- Third 1752-1688.1997.tb03556.x\n"
        )
        records, warnings = publication.extract_reference_dois_with_warnings(
            markdown,
            publication.extract_headings(markdown),
            "https://doi.org/10.9999/source",
        )
        self.assertEqual([item["doi"] for item in records], ["10.5194/hess-6-883-2002", "10.1111/j"])
        self.assertEqual(records[0]["source_location"]["line_end"], 3)
        self.assertFalse(warnings)
        self.assertEqual(publication.normalize_extracted_doi(records[1]["doi"]), "10.1111/j")

    def test_valid_doi_shapes_are_accepted_without_namespace_configuration(self) -> None:
        """Unseen, short, Springer-like, and ASCE-like DOI suffixes remain opaque."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel([{"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"}])
            fixture.write_bibtex([{"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one"}}])
            fixture.write_overrides()
            fixture.write_artifacts(
                "1",
                "# Data Availability\nUnseen https://doi.org/10.987654321/new-space.\n"
                "# References\nSpringer-like https://doi.org/10.1007/s11069-016-2382\n"
                "ASCE-like https://doi.org/10.1061/(ASCE)WR.1943-5452\n"
                "Short https://doi.org/10.7777/a\n",
            )
            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            record = corpus["publications"][0]
            self.assertEqual(
                [item["doi"] for item in record["content"]["reference_dois"]],
                ["10.1007/s11069-016-2382", "10.1061/(asce)wr.1943-5452", "10.7777/a"],
            )
            self.assertEqual(
                [item["identifier_value"] for item in record["content"]["availability_identifiers"]],
                ["10.987654321/new-space"],
            )
            validation = publication.validate_corpus(corpus, fixture.raw, 1)
            self.assertTrue(validation["valid"], validation["issues"])

    def test_production_parser_has_no_residual_corpus_specific_branches(self) -> None:
        """Production DOI decisions contain no current residual values or publisher completeness tables."""

        source = Path(publication.__file__).read_text(encoding="utf-8")
        self.assertNotIn("10.1061/(asce)", source.casefold())
        self.assertNotIn("10.1175/mwr-d-21", source.casefold())
        for forbidden_name in (
            "doi_namespace_allowlist",
            "doi_namespace_denylist",
            "provider_completeness",
            "publisher_completeness",
            "doi_suffix_minimum_length",
        ):
            self.assertNotIn(forbidden_name, source.casefold())
        self.assertNotRegex(
            source,
            r"if\s+local_paper_id\s*==\s*['\"](?:10|27|29|46|64|118|134|285)['\"]",
        )

    def test_exact_local_full_doi_evidence_repairs_an_incomplete_occurrence(self) -> None:
        """One unique exact local extension repairs an incomplete DOI without external lookup."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel([
                {"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"},
                {"id": 2, "ZoteroID": "Two_2024", "title": "Two", "year": 2024, "doi": "10.1111/two", "url": None, "journal": "Journal"},
            ])
            fixture.write_bibtex([
                {"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one"}},
                {"key": "Two_2024", "fields": {"title": "Two", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/two"}},
            ])
            fixture.write_overrides()
            citation = "Doe, J. 2004. Exact local evidence title for deterministic repair. Journal 12, 101–110."
            fixture.write_artifacts("1", f"# References\n{citation} https://doi.org/10.7777/item-10\n")
            fixture.write_artifacts("2", f"# References\n{citation} https://doi.org/10.7777/item-10-final\n")
            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            first = corpus["publications"][0]
            self.assertEqual([item["doi"] for item in first["content"]["reference_dois"]], ["10.7777/item-10-final"])
            warning = next(item for item in first["reconciliation"]["warnings"] if item["category"] == "repaired_reference_doi_candidate")
            self.assertEqual(warning["detail"]["candidate"], "10.7777/item-10")

    def test_split_availability_doi_uses_shared_source_bounded_parser(self) -> None:
        """Availability DOI parsing recovers a source-adjacent Zenodo object suffix."""

        markdown = "# Data Availability\nData: https://doi.org/10.5281/zenodo. 13974112\n"
        identifiers = publication.extract_availability_identifiers(
            markdown,
            publication.extract_headings(markdown),
            "https://doi.org/10.9999/source",
        )
        self.assertEqual(
            [(item["identifier_scheme"], item["identifier_value"]) for item in identifiers],
            [("doi", "10.5281/zenodo.13974112")],
        )

    def test_shorter_base_doi_is_not_replaced_by_a_shared_prefix(self) -> None:
        """A complete base destination survives longer chapter, version, and service values."""

        base = "10.7777/978-0-00-000000-0"
        references = [
            {"doi": base, "reference_text": "Editor, A. 2020. Complete book title. Press."},
            {"doi": f"{base}_7", "reference_text": "Writer, B. 2020. Different chapter title. In Complete book title."},
            {"doi": f"{base}/1", "reference_text": "Writer, B. 2021. Version record title. Archive."},
            {"doi": f"{base}/bibtex", "reference_text": "Service export URL."},
        ]
        self.assertIsNone(publication.exact_local_extension_repair(base, references[0]["reference_text"], references))
        self.assertEqual(publication.extract_dois_from_text(f"<https://doi.org/{base}>"), [base])
        self.assertFalse(publication.is_malformed_doi_fragment(base, f"DOI {base}; export https://example.org/bibtex"))

    def test_corrected_doi_occurrences_aggregate_deterministically(self) -> None:
        """Equivalent repaired values collapse without losing ordered occurrence evidence."""

        markdown = (
            "# References\n"
            "First https://doi.org/10.5281/ze nodo.839854.\n"
            "Second https://doi.org/10.5281/zenodo.839854.\n"
        )
        records = publication.extract_reference_dois(
            markdown,
            publication.extract_headings(markdown),
            "https://doi.org/10.9999/source",
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["doi"], "10.5281/zenodo.839854")
        self.assertEqual(len(records[0]["occurrences"]), 2)

    def test_staged_url_extraction_and_doi_resolver_classification(self) -> None:
        """URL extraction keeps clean destinations and never duplicates DOI resolvers."""

        text = (
            "[GitHub](https://github.com/AlabamaWaterInstitute/NWM-ML) "
            "https://example.org/data). "
            "[DOI](https://doi.org/10.1234/EXAMPLE) "
            "https://github.com/AlabamaWater](https://github.com/AlabamaWaterInstitute/NWM-ML)"
        )
        identifiers = [(scheme, value) for _, scheme, value in publication.extract_text_identifiers(text)]
        self.assertEqual(
            identifiers,
            [
                ("url", "https://github.com/AlabamaWaterInstitute/NWM-ML"),
                ("url", "https://example.org/data"),
                ("doi", "10.1234/example"),
            ],
        )
        self.assertFalse(any("](" in value for _, value in identifiers))
        self.assertFalse(any(scheme == "url" and "doi.org" in value for scheme, value in identifiers))

    def test_section_boundaries_abstract_keywords_and_availability(self) -> None:
        """Any next heading and explicit terminal labels stop controlled sections."""

        markdown = (
            "# Abstract\nA concise abstract.\n"
            "**Keywords:** ** Alaska · Flood • _Water_\n"
            "author@example.org\nDepartment of Hydrology\n"
            "## Data Availability\n"
            "Data at [archive](https://example.org/archive). **References** Ref https://doi.org/10.9999/ref\n"
            "#### References\nReference https://doi.org/10.8888/reference\n"
            "## Keywords\nRiver; Ice\n"
            "#### Methods\nThis is not a keyword.\n"
        )
        headings = publication.extract_headings(markdown)
        abstract, source = publication.extract_abstract(markdown, headings, "https://doi.org/10.1111/source")
        keywords, warnings = publication.extract_keywords(markdown, headings, "https://doi.org/10.1111/source", None)
        availability = publication.extract_availability_identifiers(markdown, headings, "https://doi.org/10.1111/source")
        self.assertEqual(abstract, "A concise abstract.")
        self.assertEqual((source["line_start"], source["line_end"]), (2, 2))
        self.assertNotIn("author@example.org", abstract)
        self.assertEqual([item["raw_value"] for item in keywords], ["Alaska", "Flood", "Water", "River", "Ice"])
        self.assertFalse(warnings)
        self.assertNotIn("This is not a keyword.", [item["raw_value"] for item in keywords])
        self.assertEqual(
            [(item["identifier_scheme"], item["identifier_value"]) for item in availability],
            [("url", "https://example.org/archive")],
        )

    def test_heading_normalization_preserves_original_heading_text(self) -> None:
        """Controlled matching removes HTML/Markdown artifacts without rewriting source text."""

        markdown = '## <span id="page-5-0"></span>**2.5 Ancillary data\nText\n'
        heading = publication.extract_headings(markdown)[0]
        self.assertEqual(heading["text"], '<span id="page-5-0"></span>**2.5 Ancillary data')
        self.assertEqual(heading["normalized_text"], "ancillary data")

    def test_validation_rejects_malformed_extracted_identifiers_and_duplicates(self) -> None:
        """Output validation independently rejects malformed and duplicate derived records."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel([{"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"}])
            fixture.write_bibtex([{"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one"}}])
            fixture.write_overrides()
            fixture.write_artifacts("1", "# References\nValid 10.1234/valid\n")
            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            record = corpus["publications"][0]
            valid = record["content"]["reference_dois"][0]
            malformed = json.loads(json.dumps(valid))
            malformed["doi"] = "10.1234/bad](https://doi.org/10.1234/good)"
            malformed["uri"] = "https://doi.org/10.1234/bad](https://doi.org/10.1234/good)"
            record["content"]["reference_dois"].append(malformed)
            record["content"]["reference_dois"].append(json.loads(json.dumps(valid)))
            record["content"]["availability_identifiers"].append(
                {
                    "section_category": "data_availability",
                    "section_title": "Data Availability",
                    "identifier_scheme": "url",
                    "identifier_value": "https://example.org/a](https://example.org/b)",
                    "identifier_uri": "https://example.org/a](https://example.org/b)",
                    "evidence_text": "bad",
                    "source_location": {"source_artifact": record["canonical_artifact_id"], "line_start": 2, "line_end": 2},
                }
            )
            malformed_availability_doi = {
                "section_category": "data_availability",
                "section_title": "Data Availability",
                "identifier_scheme": "doi",
                "identifier_value": "10.7777/bad](https://doi.org/10.7777/good)",
                "identifier_uri": "https://doi.org/10.7777/bad](https://doi.org/10.7777/good)",
                "evidence_text": "10.7777/bad](https://doi.org/10.7777/good)",
                "source_location": {"source_artifact": record["canonical_artifact_id"], "line_start": 2, "line_end": 2},
            }
            record["content"]["availability_identifiers"].append(malformed_availability_doi)
            corpus["summary"] = publication.calculate_summary(corpus, 1, 1)
            validation = publication.validate_corpus(corpus, fixture.raw, 1)
            self.assertFalse(validation["valid"])
            self.assertTrue(any("malformed extracted reference DOI" in issue for issue in validation["issues"]))
            self.assertTrue(any("duplicate reference DOI record" in issue for issue in validation["issues"]))
            self.assertTrue(any("malformed availability URL" in issue for issue in validation["issues"]))
            self.assertTrue(any("malformed availability DOI" in issue for issue in validation["issues"]))

    def test_generic_overrides_natural_order_and_known_exclusion(self) -> None:
        """Declarative replacement/addition rules work without publication-specific branches."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel(
                [
                    {"id": 10, "ZoteroID": None, "title": "Final", "year": 2025, "doi": "10.9999/final", "url": None, "journal": "Journal"},
                    {"id": "2-extra", "ZoteroID": None, "title": "Correction", "year": 2024, "doi": "10.9999/correction", "url": None, "journal": "Journal"},
                    {"id": 2, "ZoteroID": "Original_2023", "title": "Original", "year": 2023, "doi": "10.9999/original", "url": None, "journal": "Journal"},
                ]
            )
            fixture.write_bibtex(
                [
                    {"key": "Original_2023", "fields": {"title": "Original", "author": "Doe, Jane", "year": "2023", "journal": "Journal", "doi": "10.9999/original"}},
                    {"key": "Preprint_2024", "fields": {"title": "Preprint", "author": "Smith, Alex", "year": "2024", "journal": "Archive"}},
                ]
            )
            author = [{"display_name": "Alex Smith", "raw_name": "Smith, Alex"}]
            fixture.write_overrides(
                {
                    "10": {
                        "action": "replace_bibliographic_record",
                        "source_zotero_key": "Preprint_2024",
                        "reason": "Final publication replaces preprint",
                        "metadata": {"record_type": "journal_article", "bibtex_entry_type": "article", "title": "Final", "authors": author, "year": 2025, "venue": "Journal", "doi": "10.9999/final"},
                    },
                    "2-extra": {
                        "action": "add_non_zotero_artifact",
                        "reason": "Separate correction",
                        "metadata": {"record_type": "corrigendum", "bibtex_entry_type": None, "title": "Correction", "authors": author, "year": 2024, "venue": "Journal", "doi": "10.9999/correction"},
                        "correction_of": {"scheme": "doi", "value": "10.9999/original", "uri": "https://doi.org/10.9999/original"},
                    },
                }
            )
            for local_id in ("10", "2-extra", "2"):
                fixture.write_artifacts(local_id)
            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            self.assertEqual([item["local_paper_id"] for item in corpus["publications"]], ["2", "2-extra", "10"])
            self.assertEqual(corpus["summary"]["override_record_count"], 2)
            self.assertEqual(corpus["summary"]["non_zotero_record_count"], 1)
            self.assertEqual(corpus["known_exclusions"][0]["source_key"], "Preprint_2024")
            self.assertEqual(corpus["publications"][1]["bibliographic_relations"]["correction_of"]["uri"], "https://doi.org/10.9999/original")

    def test_identifier_dispositions_are_exact_auditable_and_fatal_when_invalid(self) -> None:
        """Declarative deferrals preserve evidence and reject unused, duplicate, or ambiguous rules."""

        base_record = {
            "id": 1,
            "ZoteroID": "One_2024",
            "title": "One",
            "year": 2024,
            "doi": "10.1111/one",
            "url": None,
            "journal": "Journal",
        }
        bibtex_record = {
            "key": "One_2024",
            "fields": {
                "title": "One",
                "author": "Doe, Jane",
                "year": "2024",
                "journal": "Journal",
                "doi": "10.1111/one",
            },
        }

        def disposition(candidate: str = "10.7777/defer") -> dict[str, object]:
            """Create one generic source-scoped reference deferral fixture."""

            return {
                "context": "reference",
                "candidate": candidate,
                "action": "defer",
                "reason": "Unresolved exact local boundary evidence.",
            }

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel([base_record])
            fixture.write_bibtex([bibtex_record])
            fixture.write_overrides({"1": {"identifier_dispositions": [disposition()]}})
            evidence = "Citation with exact evidence https://doi.org/10.7777/defer"
            fixture.write_artifacts("1", f"# References\n{evidence}\n")
            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            record = corpus["publications"][0]
            self.assertFalse(record["content"]["reference_dois"])
            warning = next(
                item for item in record["reconciliation"]["warnings"]
                if item["category"] == "deferred_reference_doi_candidate"
            )
            self.assertEqual(warning["detail"]["candidate"], "10.7777/defer")
            self.assertEqual(warning["detail"]["evidence_text"], evidence)
            self.assertEqual(warning["detail"]["source_location"]["line_start"], 2)
            self.assertEqual(record["reconciliation"]["override_applied"], False)

        for case, dispositions, markdown in (
            ("unused", [disposition("10.7777/missing")], "# References\nCitation 10.7777/defer\n"),
            ("duplicate", [disposition(), disposition()], "# References\nCitation 10.7777/defer\n"),
            (
                "overlapping",
                [
                    disposition(),
                    {
                        **disposition(),
                        "reason": "A second rule overlaps the same exact occurrence.",
                    },
                ],
                "# References\nCitation 10.7777/defer\n",
            ),
            (
                "ambiguous",
                [disposition()],
                "# References\nFirst 10.7777/defer\nSecond 10.7777/defer\n",
            ),
        ):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                fixture = PublicationFixture(Path(temporary))
                fixture.write_excel([base_record])
                fixture.write_bibtex([bibtex_record])
                fixture.write_overrides({"1": {"identifier_dispositions": dispositions}})
                fixture.write_artifacts("1", markdown)
                with self.assertRaises(publication.CorpusBuildError):
                    publication.build_corpus(fixture.raw, fixture.overrides)

    def test_comparison_artifact_is_irrelevant_and_serialization_is_stable(self) -> None:
        """Comparison-only JSON presence and content cannot affect deterministic output."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel([{"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"}])
            fixture.write_bibtex([{"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one"}}])
            fixture.write_overrides()
            fixture.write_artifacts("1")
            comparison = fixture.raw / "publication_artifacts.json"
            comparison.write_text('{"forbidden": "first"}', encoding="utf-8")
            first = publication.serialize_corpus(publication.build_corpus(fixture.raw, fixture.overrides))
            comparison.write_text('{"forbidden": "second", "more": true}', encoding="utf-8")
            second = publication.serialize_corpus(publication.build_corpus(fixture.raw, fixture.overrides))
            comparison.unlink()
            third = publication.serialize_corpus(publication.build_corpus(fixture.raw, fixture.overrides))
            self.assertEqual(first, second)
            self.assertEqual(second, third)
            self.assertTrue(first.endswith(b"\n"))
            self.assertFalse(first.endswith(b"\n\n"))
            self.assertNotIn(b"forbidden", first)

    def test_production_doi_policy_contains_no_snapshot_specific_exceptions(self) -> None:
        """Production source has no removed shape tables or current-corpus DOI exceptions."""

        source = Path(publication.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "INCOMPLETE_" + "PROVIDER_DOI_PATTERN",
            "INCOMPLETE_" + "PUBLISHER_STEM_PATTERN",
            "INCOMPLETE_" + "ASCE_DOI_PATTERN",
            "INCOMPLETE_" + "SPRINGER_LEGACY_DOI_PATTERN",
            "BOOK_" + "DOI_PATTERN",
            "10.1007/s11069-016-2382",
            "10.1061/(asce)wr.1943-5452",
        ):
            self.assertNotIn(forbidden, source)

    def test_validation_failure_does_not_overwrite_output(self) -> None:
        """A missing required artifact fails before an existing output is touched."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = PublicationFixture(root)
            fixture.write_excel([{"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"}])
            fixture.write_bibtex([{"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one"}}])
            fixture.write_overrides()
            fixture.write_artifacts("1")
            (fixture.raw / "markdowns/1/chunks/1_chunks.json").unlink()
            output = root / "existing.json"
            output.write_bytes(b"preserve-me")
            status = publication.main(
                ["--raw-root", str(fixture.raw), "--output", str(output), "--overrides", str(fixture.overrides), "--expected-record-count", "1"]
            )
            self.assertEqual(status, 1)
            self.assertEqual(output.read_bytes(), b"preserve-me")

    def test_validation_rejects_local_identifier_and_hash_metadata(self) -> None:
        """Technical local IDs and per-file hashes cannot enter public identifiers or metadata."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel([{"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"}])
            fixture.write_bibtex([{"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one"}}])
            fixture.write_overrides()
            fixture.write_artifacts("1")
            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            corpus["publications"][0]["identifiers"].append({"scheme": "local", "value": "1", "uri": "1"})
            corpus["publications"][0]["source_files"]["pdf_sha256"] = "bad"
            validation = publication.validate_corpus(corpus, fixture.raw, 1)
            self.assertFalse(validation["valid"])
            self.assertTrue(any("identifier scheme" in issue for issue in validation["issues"]))
            self.assertTrue(any("SHA-256" in issue for issue in validation["issues"]))

    def test_abstract_uses_first_logical_block_and_stops_before_nonvisible_body(self) -> None:
        """An unheaded body paragraph, image, or caption cannot extend an abstract."""

        for suffix in (
            "Unheaded introduction body.\n",
            "![](figure.png)\n",
            "Figure 1. Study area.\n",
        ):
            markdown = "# Abstract\nA concise abstract paragraph.\n\n" + suffix + "\n## Main Text\nBody.\n"
            headings = publication.extract_headings(markdown)
            abstract, source = publication.extract_abstract(markdown, headings, "https://doi.org/10.1111/source")
            self.assertEqual(abstract, "A concise abstract paragraph.")
            self.assertEqual((source["line_start"], source["line_end"]), (2, 2))

    def test_structured_and_long_abstracts_are_retained_without_length_rejection(self) -> None:
        """Approved structured labels continue an abstract and length alone is not rejection evidence."""

        markdown = (
            "# Abstract\nContext: The problem context.\n\n"
            "**Methods:**\n\nThe study method.\n\n*Results:* The result.\n\n"
            "Ordinary unheaded article prose.\n"
        )
        abstract, _, reason = publication.extract_abstract_with_disposition(
            markdown,
            publication.extract_headings(markdown),
            "https://doi.org/10.1111/source",
        )
        self.assertEqual(
            abstract,
            "Context: The problem context.\n\n**Methods:**\n\nThe study method.\n\n*Results:* The result.",
        )
        self.assertIsNone(reason)
        long_markdown = "# Abstract\n" + ("Hydrologic evidence remains valid. " * 220) + "\n"
        long_abstract, _, long_reason = publication.extract_abstract_with_disposition(
            long_markdown,
            publication.extract_headings(long_markdown),
            "https://doi.org/10.1111/source",
        )
        self.assertGreater(len(long_abstract), publication.ABSTRACT_AUDIT_CHARACTER_THRESHOLD)
        self.assertIsNone(long_reason)

    def test_contaminated_abstract_falls_back_to_bibtex_or_null_with_warning(self) -> None:
        """Rejected explicit Markdown uses only an available explicit BibTeX fallback."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel(
                [
                    {"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"},
                    {"id": 2, "ZoteroID": "Two_2024", "title": "Two", "year": 2024, "doi": "10.1111/two", "url": None, "journal": "Journal"},
                ]
            )
            fixture.write_bibtex(
                [
                    {"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one", "abstract": "BibTeX fallback abstract."}},
                    {"key": "Two_2024", "fields": {"title": "Two", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/two"}},
                ]
            )
            fixture.write_overrides()
            contaminated = "# Abstract\nCandidate with inline ![figure](image.png) contamination.\n"
            fixture.write_artifacts("1", contaminated)
            fixture.write_artifacts("2", contaminated)
            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            first, second = corpus["publications"]
            self.assertEqual(first["bibliographic"]["abstract"], "BibTeX fallback abstract.")
            self.assertEqual(first["bibliographic"]["abstract_source"]["source_type"], "bibtex_explicit")
            self.assertIsNone(second["bibliographic"]["abstract"])
            self.assertIsNone(second["bibliographic"]["abstract_source"])
            for record in (first, second):
                warnings = record["reconciliation"]["warnings"]
                rejected = [item for item in warnings if item["category"] == "markdown_abstract_rejected"]
                self.assertEqual(rejected[0]["detail"]["reason"], "contains_image")

    def test_keyword_block_stops_at_blank_or_metadata_boundary(self) -> None:
        """Only the first contiguous declaration block contributes keywords."""

        markdown = (
            "# Keywords\nHydrology; Forecasting\n\nAbstract prose must not enter.\n"
            "## Key words\nFlood | Streamflow\nDOI: 10.1234/example\n"
            "## Author keywords\nWater\nCorresponding author: author@example.org\n"
        )
        keywords, warnings = publication.extract_keywords(
            markdown,
            publication.extract_headings(markdown),
            "https://doi.org/10.1111/source",
            None,
        )
        self.assertEqual(
            [item["raw_value"] for item in keywords],
            ["Hydrology", "Forecasting", "Flood", "Streamflow", "Water"],
        )
        self.assertEqual(
            sum(item["category"] == "keyword_section_stopped_at_metadata" for item in warnings),
            2,
        )

    def test_keyword_separator_forms_cleaning_and_order(self) -> None:
        """Pipe, TeX dots, bullets, and middle dots are explicit ordered separators."""

        declarations = (
            "Alpha | Beta ｜ Gamma ¦ Delta ǀ Epsilon; "
            r"Zeta $\cdot$ Eta \( \cdot \) Theta \bullet Iota $\bullet$ Kappa · Lambda • Mu"
        )
        keywords, warnings = publication.keyword_candidates_from_declaration(
            declarations,
            7,
            "markdown_explicit",
            "https://doi.org/10.1111/source",
            "Keywords",
        )
        self.assertFalse(warnings)
        self.assertEqual(
            [item["raw_value"] for item in keywords],
            ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu"],
        )
        self.assertEqual(publication.clean_keyword_value("** Alaska"), "Alaska")
        self.assertEqual(publication.clean_keyword_value("model)"), "model")

    def test_keyword_ambiguity_and_contamination_are_precision_first(self) -> None:
        """Long undelimited lists and front-matter values are omitted without semantic splitting."""

        ambiguous = "Operational flood forecasting model Global discharge Cloud computing United States Fluvial flood"
        keywords, warnings = publication.keyword_candidates_from_declaration(
            ambiguous,
            12,
            "markdown_explicit",
            "https://doi.org/10.1111/source",
            "Keywords",
        )
        self.assertFalse(keywords)
        self.assertEqual(warnings[0]["category"], "ambiguous_keyword_declaration")
        self.assertEqual(warnings[0]["detail"]["candidate"], ambiguous)
        short, short_warnings = publication.keyword_candidates_from_declaration(
            "Hydrologic model",
            13,
            "markdown_explicit",
            "https://doi.org/10.1111/source",
            "Keywords",
        )
        self.assertEqual([item["raw_value"] for item in short], ["Hydrologic model"])
        self.assertFalse(short_warnings)
        rejected_values = (
            "author@example.org",
            "DOI: 10.1234/example",
            "Copyright 2025 Publisher",
            "Received 4 January 2025",
            "Department of Hydrology",
            "Supplementary information is available online",
        )
        for value in rejected_values:
            self.assertIsNotNone(publication.validate_keyword_candidate(value), value)

    def test_keyword_ambiguity_threshold_has_exact_candidate_semantics(self) -> None:
        """Six undelimited tokens defer, five remain eligible, and separators take precedence."""

        self.assertEqual(publication.AMBIGUOUS_KEYWORD_CHARACTER_THRESHOLD, 80)
        self.assertEqual(publication.AMBIGUOUS_KEYWORD_TOKEN_THRESHOLD, 6)
        six = "Nutrient load estimation Random forest WRTDS"
        deferred, warnings = publication.keyword_candidates_from_declaration(
            six,
            4,
            "markdown_explicit",
            "https://doi.org/10.1111/source",
            "Keywords",
        )
        self.assertFalse(deferred)
        self.assertEqual(warnings[0]["category"], "ambiguous_keyword_declaration")
        self.assertEqual(warnings[0]["detail"]["candidate"], six)
        for five in (
            "machine learning models at edge",
            "Deep learning graphical user interface",
        ):
            emitted, emitted_warnings = publication.keyword_candidates_from_declaration(
                five,
                5,
                "markdown_explicit",
                "https://doi.org/10.1111/source",
                "Keywords",
            )
            self.assertEqual([item["raw_value"] for item in emitted], [five])
            self.assertFalse(emitted_warnings)
        separated, separated_warnings = publication.keyword_candidates_from_declaration(
            "one two three; four five six; seven eight nine",
            6,
            "markdown_explicit",
            "https://doi.org/10.1111/source",
            "Keywords",
        )
        self.assertEqual(len(separated), 3)
        self.assertFalse(separated_warnings)

    def test_keyword_presentation_punctuation_and_cleanup_deduplication(self) -> None:
        """List punctuation is removed without changing semantic internal punctuation."""

        expectations = {
            "— Acoustic sensing": "Acoustic sensing",
            "– Flood Risk": "Flood Risk",
            "Artificial intelligence.": "Artificial intelligence",
            "slumping failure.": "slumping failure",
            "access (TDMA).": "access (TDMA)",
            "physics-informed learning": "physics-informed learning",
            "version 2.0 model": "version 2.0 model",
            "U.S.": "U.S.",
        }
        for source, expected in expectations.items():
            self.assertEqual(publication.clean_keyword_value(source), expected)
        markdown = "**Keywords:** Flood.; Flood; physics-informed learning\n"
        keywords, warnings = publication.extract_keywords(
            markdown,
            publication.extract_headings(markdown),
            "https://doi.org/10.1111/source",
            None,
        )
        self.assertFalse(warnings)
        self.assertEqual(
            [item["raw_value"] for item in keywords],
            ["Flood", "physics-informed learning"],
        )

    def test_marker_control_characters_are_audited_and_sanitized_positionally(self) -> None:
        """Every Markdown derivative uses a same-length sanitized copy while raw bytes stay immutable."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel([{"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"}])
            fixture.write_bibtex([{"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one"}}])
            fixture.write_overrides()
            markdown = (
                "# Abstract\nA clean\x02 abstract.\n"
                "# Keywords\nHydro\x0flogy; Streamflow\n"
                "# References\nCitation 10.1234/example\x10.\n"
                "# Data Availability\nData at https://example.org/archive\x13.\n"
                "## Meth\x01ods\nBody.\n"
            )
            fixture.write_artifacts("1", markdown)
            raw_path = fixture.raw / "markdowns/1/markdown/1_md.md"
            metadata_path = fixture.raw / "markdowns/1/markdown/1_md_meta.json"
            marker_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            marker_metadata["table_of_contents"] = [{"title": "Meta\x1cdata"}]
            metadata_path.write_text(json.dumps(marker_metadata), encoding="utf-8")
            raw_before = raw_path.read_bytes()
            first = publication.build_corpus(fixture.raw, fixture.overrides)
            second = publication.build_corpus(fixture.raw, fixture.overrides)
            self.assertEqual(raw_path.read_bytes(), raw_before)
            self.assertEqual(publication.serialize_corpus(first), publication.serialize_corpus(second))
            record = first["publications"][0]
            self.assertEqual(record["bibliographic"]["abstract"], "A clean  abstract.")
            self.assertEqual(
                (record["bibliographic"]["abstract_source"]["line_start"], record["bibliographic"]["abstract_source"]["line_end"]),
                (2, 2),
            )
            self.assertIn("Hydro logy", [item["raw_value"] for item in record["content"]["explicit_keywords"]])
            heading = next(item for item in record["content"]["headings"] if "Meth" in item["text"])
            self.assertEqual(heading["text"], "Meth ods")
            self.assertEqual(heading["normalized_text"], "meth ods")
            self.assertEqual(record["document_structure"]["table_of_contents"], [{"title": "Meta data"}])
            reference = record["content"]["reference_dois"][0]
            availability = record["content"]["availability_identifiers"][0]
            self.assertFalse(publication.CONTROL_PATTERN.search(reference["reference_text"]))
            self.assertFalse(publication.CONTROL_PATTERN.search(availability["evidence_text"]))
            control_warnings = [
                item for item in record["reconciliation"]["warnings"]
                if item["category"] == "unexpected_control_characters"
            ]
            self.assertEqual(len(control_warnings), 1)
            self.assertEqual(
                control_warnings[0]["detail"],
                {
                    "source_path": "papers/markdowns/1/markdown/1_md.md",
                    "occurrence_count": 5,
                    "code_points": ["U+0001", "U+0002", "U+000F", "U+0010", "U+0013"],
                    "line_numbers": [2, 4, 6, 8, 9],
                },
            )
            self.assertFalse(publication.find_forbidden_control_characters(first))

    def test_recursive_validation_rejects_control_from_non_marker_source(self) -> None:
        """A control introduced anywhere in the assembled corpus fails with its field path."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel([{"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"}])
            fixture.write_bibtex([{"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one"}}])
            fixture.write_overrides()
            fixture.write_artifacts("1")
            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            corpus["publications"][0]["bibliographic"]["title"] = "Bad\x01 title"
            validation = publication.validate_corpus(corpus, fixture.raw, 1)
            self.assertFalse(validation["valid"])
            self.assertTrue(
                any(
                    "$.publications[0].bibliographic.title" in issue and "U+0001" in issue
                    for issue in validation["issues"]
                )
            )

    def test_validation_rejects_contaminated_abstract_and_keyword(self) -> None:
        """Corpus validation independently enforces abstract and keyword quality."""

        with tempfile.TemporaryDirectory() as temporary:
            fixture = PublicationFixture(Path(temporary))
            fixture.write_excel([{"id": 1, "ZoteroID": "One_2024", "title": "One", "year": 2024, "doi": "10.1111/one", "url": None, "journal": "Journal"}])
            fixture.write_bibtex([{"key": "One_2024", "fields": {"title": "One", "author": "Doe, Jane", "year": "2024", "journal": "Journal", "doi": "10.1111/one"}}])
            fixture.write_overrides()
            fixture.write_artifacts("1", "# Abstract\nValid abstract.\n## Keywords\nHydrology\n")
            corpus = publication.build_corpus(fixture.raw, fixture.overrides)
            record = corpus["publications"][0]
            record["bibliographic"]["abstract"] = "Invalid ![figure](image.png)"
            record["content"]["explicit_keywords"][0]["raw_value"] = "author@example.org"
            record["content"]["explicit_keywords"][0]["value"] = "author@example.org"
            corpus["summary"] = publication.calculate_summary(corpus, 1, 1)
            validation = publication.validate_corpus(corpus, fixture.raw, 1)
            self.assertFalse(validation["valid"])
            self.assertTrue(any("Markdown abstract is contaminated" in issue for issue in validation["issues"]))
            self.assertTrue(any("invalid explicit keyword" in issue for issue in validation["issues"]))


@unittest.skipUnless(FROZEN_RAW.exists() and FROZEN_OVERRIDES.exists(), "Frozen publication corpus unavailable")
class PublicationPhaseAFrozenRegressionTests(unittest.TestCase):
    """Validate the current curated 228-publication snapshot explicitly."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build and validate the frozen corpus once for all regression assertions."""

        cls.corpus = publication.build_corpus(FROZEN_RAW, FROZEN_OVERRIDES)
        cls.validation = publication.validate_corpus(cls.corpus, FROZEN_RAW, 228, True)
        cls.by_id = {record["local_paper_id"]: record for record in cls.corpus["publications"]}

    def test_frozen_counts_and_validation(self) -> None:
        """The frozen roster and source reconciliation match all contract anchors."""

        self.assertTrue(self.validation["valid"], self.validation["issues"])
        summary = self.corpus["summary"]
        self.assertEqual(summary["excel_record_count"], 228)
        self.assertEqual(summary["bibtex_entry_count"], 227)
        self.assertEqual(summary["publication_count"], 228)
        self.assertEqual(summary["by_record_type"], {"book_chapter": 1, "conference_paper": 5, "corrigendum": 1, "journal_article": 221})
        self.assertEqual(summary["exact_bibtex_matches"], 212)
        self.assertEqual(summary["encoding_repair_matches"], 14)
        self.assertEqual(summary["override_record_count"], 2)
        self.assertEqual(summary["papers_with_explicit_keywords"], 70)
        self.assertEqual(summary["explicit_keyword_count"], 373)
        self.assertEqual(summary["reference_doi_count"], 8856)
        self.assertEqual(summary["papers_with_availability_identifiers"], 73)
        self.assertEqual(summary["availability_identifier_count"], 299)
        self.assertEqual(summary["warning_count"], 147)
        reference_values = {
            item["doi"]
            for record in self.corpus["publications"]
            for item in record["content"]["reference_dois"]
        }
        self.assertEqual(len(reference_values), 6720)
        self.assertEqual(
            sum(
                len(item["occurrences"])
                for record in self.corpus["publications"]
                for item in record["content"]["reference_dois"]
            ),
            8963,
        )
        self.assertEqual(self.corpus["schema_version"], "1.1.0")
        self.assertEqual(self.corpus["phase_a_version"], "1.0.9")

    def test_frozen_special_records(self) -> None:
        """Required records retain their exact identity and curation disposition."""

        self.assertEqual(self.by_id["71"]["canonical_artifact_id"], "https://doi.org/10.5194/hess-29-547-2025")
        self.assertEqual(self.by_id["71"]["reconciliation"]["override_action"], "replace_bibliographic_record")
        self.assertEqual(self.by_id["87"]["canonical_artifact_id"], "https://doi.org/10.5194/hess-26-3377-2022")
        self.assertEqual(self.by_id["87-corrigendum"]["record_type"], "corrigendum")
        self.assertEqual(self.by_id["87-corrigendum"]["bibliographic_relations"]["correction_of"]["uri"], "https://doi.org/10.5194/hess-26-3377-2022")
        self.assertEqual(self.by_id["93"]["bibliographic"]["title"], "EASYMORE: A Python package to streamline the remapping of variables for Earth System models")
        self.assertEqual(self.by_id["109"]["canonical_identifier"]["scheme"], "url")
        self.assertEqual(self.by_id["207"]["bibliographic"]["title"], "Nature-based solutions as buffers against coastal compound flooding: Exploring potential framework for process-based modeling of hazard mitigation")

    def test_frozen_output_has_no_kg_or_disallowed_metadata(self) -> None:
        """Phase A remains page data rather than a graph or EvidenceSpan artifact."""

        serialized = publication.serialize_corpus(self.corpus)
        self.assertNotIn(b'"nodes"', serialized)
        self.assertNotIn(b'"edges"', serialized)
        self.assertNotIn(b'"EvidenceSpan"', serialized)
        self.assertNotIn(b'"markdown":', serialized)
        self.assertFalse(publication.contains_forbidden_hash_key(self.corpus))
        self.assertTrue(all(identifier["scheme"] in {"doi", "url"} for record in self.corpus["publications"] for identifier in record["identifiers"]))

    def test_frozen_derived_identifiers_are_strict_and_unique(self) -> None:
        """Frozen Markdown derivatives contain no wrappers, malformed values, or duplicates."""

        for record in self.corpus["publications"]:
            dois = [item["doi"] for item in record["content"]["reference_dois"]]
            self.assertEqual(len(dois), len(set(dois)), record["local_paper_id"])
            for item in record["content"]["reference_dois"]:
                self.assertEqual(publication.normalize_extracted_doi(item["doi"]), item["doi"])
                self.assertFalse(
                    publication.is_malformed_doi_fragment(item["doi"], item["reference_text"]),
                    (record["local_paper_id"], item["doi"]),
                )
                self.assertNotRegex(item["doi"], r"[\[\]]|https?://|doi\.org")
                self.assertEqual(item["uri"], f"https://doi.org/{item['doi']}")
            availability = [
                (item["identifier_scheme"], item["identifier_value"])
                for item in record["content"]["availability_identifiers"]
            ]
            self.assertEqual(len(availability), len(set(availability)), record["local_paper_id"])
            for item in record["content"]["availability_identifiers"]:
                if item["identifier_scheme"] == "url":
                    self.assertEqual(publication.normalize_extracted_url(item["identifier_value"]), item["identifier_value"])
                    self.assertNotIn("](", item["identifier_value"])
                    self.assertFalse(publication.is_doi_resolver_url(item["identifier_value"]))

        known_fragments = {
            "10.1016/j",
            "10.1111/j",
            "10.3389/feart",
            "10.1038/natur",
            "10.5194/he",
            "10.5281/ze",
            "10.31223/osf",
            "10.1175/mwr-d",
        }
        emitted = {
            item["doi"]
            for record in self.corpus["publications"]
            for item in record["content"]["reference_dois"]
        }
        self.assertFalse(known_fragments.intersection(emitted))

    def test_frozen_residual_malformed_dois_are_repaired_or_omitted(self) -> None:
        """All five independently reported malformed values have explicit dispositions."""

        forbidden = {
            "10.1007/s11069-004-4549",
            "10.1007/s11069-016-2382",
            "10.1175/mwr-d-21",
            "10.1061/(asce)",
            "10.5194/hess-15-3399",
            "10.1061/(asce)wr.1943-5452",
            "10.5281/zenodo",
        }
        emitted = {
            item["doi"]
            for record in self.corpus["publications"]
            for item in record["content"]["reference_dois"]
        } | {
            item["identifier_value"]
            for record in self.corpus["publications"]
            for item in record["content"]["availability_identifiers"]
            if item["identifier_scheme"] == "doi"
        }
        self.assertFalse(forbidden.intersection(emitted))
        self.assertIn("10.1007/s11069-004-4549-4", {item["doi"] for item in self.by_id["10"]["content"]["reference_dois"]})
        self.assertIn("10.5194/hess-15-3399-2011", {item["doi"] for item in self.by_id["118"]["content"]["reference_dois"]})
        self.assertIn(
            ("doi", "10.5281/zenodo.13974112"),
            {(item["identifier_scheme"], item["identifier_value"]) for item in self.by_id["285"]["content"]["availability_identifiers"]},
        )
        for local_id, candidate in (
            ("27", "10.1007/s11069-016-2382"),
            ("29", "10.1175/mwr-d-21"),
            ("46", "10.1061/(asce)"),
            ("134", "10.1061/(asce)wr.1943-5452"),
        ):
            warnings = [
                item for item in self.by_id[local_id]["reconciliation"]["warnings"]
                if item["category"] == "deferred_reference_doi_candidate"
                and item["detail"]["candidate"] == candidate
            ]
            self.assertEqual(len(warnings), 1)
            warning = warnings[0]
            self.assertEqual(warning["detail"]["candidate"], candidate)
            self.assertEqual(warning["detail"]["action"], "defer")
            self.assertTrue(warning["detail"]["evidence_text"])
            self.assertEqual(warning["detail"]["source_location"]["source_artifact"], warning["detail"]["source_artifact"])
        self.assertIn(
            "invalid_split_doi_continuation",
            next(
                item for item in self.by_id["46"]["reconciliation"]["warnings"]
                if item["category"] == "deferred_reference_doi_candidate"
                and item["detail"]["candidate"] == "10.1061/(asce)"
            )["detail"]["reason"],
        )
        self.assertIn(
            "10.1002/met.119",
            {item["doi"] for item in self.by_id["64"]["content"]["reference_dois"]},
        )
        overrides = publication.load_overrides(FROZEN_OVERRIDES)
        paper_29_dispositions = overrides["29"]["identifier_dispositions"]
        self.assertEqual(len(paper_29_dispositions), 1)
        self.assertEqual(paper_29_dispositions[0]["context"], "reference")
        self.assertEqual(paper_29_dispositions[0]["candidate"], "10.1175/mwr-d-21")
        self.assertEqual(paper_29_dispositions[0]["action"], "defer")
        self.assertNotIn("46", overrides)

    def test_frozen_cli_builds_are_byte_identical_across_processes(self) -> None:
        """Two independent interpreter processes serialize the frozen corpus identically."""

        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.json"
            second = Path(temporary) / "second.json"
            base = [
                sys.executable,
                "-m",
                "src.preprocessing.build_publication_corpus",
                "--raw-root",
                str(FROZEN_RAW),
                "--overrides",
                str(FROZEN_OVERRIDES),
                "--validate-frozen-snapshot",
            ]
            subprocess.run([*base, "--output", str(first)], check=True, capture_output=True, text=True)
            subprocess.run([*base, "--output", str(second)], check=True, capture_output=True, text=True)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_frozen_abstract_and_keyword_regressions(self) -> None:
        """Known source-layout regressions exercise only generic parser behavior."""

        abstract = self.by_id["244"]["bibliographic"]["abstract"]
        self.assertTrue(abstract.startswith("Climate risk assessments typically focus on large rivers"))
        self.assertTrue(abstract.endswith("elucidates the fine-scale distribution of climate risks across communities."))
        self.assertNotIn("Climate impact assessments for water supply", abstract)
        self.assertNotIn("Figure 1", abstract)
        self.assertNotIn("Main Text", abstract)
        self.assertEqual(
            [item["raw_value"] for item in self.by_id["265"]["content"]["explicit_keywords"]],
            ["Hydrology", "Hydrometeorology", "Uncertainty", "Ensembles", "Hydrologic models", "Forcing"],
        )
        self.assertEqual(len(self.by_id["84"]["content"]["explicit_keywords"]), 7)
        self.assertEqual(len(self.by_id["141"]["content"]["explicit_keywords"]), 7)

    def test_frozen_keywords_have_no_front_matter_or_ambiguous_values(self) -> None:
        """No emitted frozen keyword violates deterministic contamination or ambiguity guards."""

        for record in self.corpus["publications"]:
            for keyword in record["content"]["explicit_keywords"]:
                self.assertIsNone(
                    publication.validate_keyword_candidate(keyword["raw_value"]),
                    (record["local_paper_id"], keyword["raw_value"]),
                )
                self.assertFalse(
                    publication.is_ambiguous_keyword_declaration(keyword["raw_value"]),
                    (record["local_paper_id"], keyword["raw_value"]),
                )
                self.assertLess(
                    len(keyword["raw_value"].split()),
                    publication.AMBIGUOUS_KEYWORD_TOKEN_THRESHOLD,
                )
                self.assertFalse(keyword["raw_value"].startswith(("—", "–")))
                self.assertFalse(
                    keyword["raw_value"].endswith(".")
                    and not re.fullmatch(r"(?:[A-Za-z]\.){2,}", keyword["raw_value"])
                )
        ambiguous_warnings = [
            item
            for record in self.corpus["publications"]
            for item in record["reconciliation"]["warnings"]
            if item["category"] == "ambiguous_keyword_declaration"
        ]
        self.assertEqual(len(ambiguous_warnings), 45)
        self.assertTrue(all(item["detail"].get("candidate") for item in ambiguous_warnings))

    def test_frozen_control_characters_are_audited_but_never_emitted(self) -> None:
        """All raw control anomalies are structured warnings and output strings are clean."""

        self.assertFalse(publication.find_forbidden_control_characters(self.corpus))
        warnings = [
            item
            for record in self.corpus["publications"]
            for item in record["reconciliation"]["warnings"]
            if item["category"] == "unexpected_control_characters"
        ]
        self.assertEqual(len(warnings), 18)
        self.assertEqual(sum(item["detail"]["occurrence_count"] for item in warnings), 44)
        self.assertEqual(
            sorted({point for item in warnings for point in item["detail"]["code_points"]}),
            ["U+0000", "U+0001", "U+0002", "U+0008", "U+000C", "U+000F", "U+0010", "U+0012", "U+0013", "U+001C"],
        )


if __name__ == "__main__":
    unittest.main()
