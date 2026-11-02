"""Two-phase offline evaluation: materialize gold-blind views, then score both."""

import argparse
import json
from pathlib import Path
import tarfile

from . import scierc_external_anchor as a
from . import scierc_official_runner as runner
from . import scierc_postrun_projection as projection
from . import scierc_smoke_runtime as s
from .openai_provider import extract_model_output, validate_provider_response

OUT = a.PROJECT_ROOT / "data/curation/papers/m2/scierc_step9_postrun_v0.1.0"
RUNTIME = a.RUNTIME_ROOT / "postrun_projections_v0.1.0"
AMENDMENT = a.PROJECT_ROOT / "docs/scierc_postrun_failure_isolation_amendment_v0.1.0.md"
DECISIONS = a.PROJECT_ROOT / "docs/evaluation_decisions.md"
MANIFEST = OUT / "projection_manifest.json"
LEDGER = OUT / "rejection_ledger.json"
EVIDENCE = OUT / "preserved_evidence.json"
A_PATH = RUNTIME / "A_record_isolation.jsonl"
B_PATH = RUNTIME / "B_document_rejection.jsonl"


def evidence(path: Path) -> dict:
    """Hash existing bytes without copying raw evidence to tracked storage."""
    raw = path.read_bytes()
    return {"path": str(path.relative_to(a.PROJECT_ROOT)), "sha256": a.sha256_bytes(raw), "sizeBytes": len(raw)}


def verify(item: dict) -> None:
    """Reject any drift from recorded evidence."""
    projection.require(evidence(a.PROJECT_ROOT / item["path"]) == item, "EVIDENCE_DRIFT:" + item["path"])


def encode(value) -> bytes:
    """Encode deterministic sanitized review JSON."""
    return json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"


def write(path: Path, raw: bytes) -> None:
    """Never overwrite authentic or already-materialized divergent bytes."""
    if path.exists():
        projection.require(path.read_bytes() == raw, "OUTPUT_CONFLICT:" + path.name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        s._write_new(path, raw)


def source_document(body: dict) -> a.SciERCDocument:
    """Recover authoritative source-only tokens from the exact prepared request."""
    value = s._strict_json(body["input"].split("\nSciERC benchmark document:\n", 1)[1].encode())
    tokens = value["tokens"]
    projection.require(all(type(row["index"]) is int and row["index"] == i and type(row["text"]) is str for i,row in enumerate(tokens)), "REQUEST_TOKEN_INDEX")
    sentences = [[row["text"] for row in tokens[item["start"]:item["end"]+1]] for item in value["sentences"]]
    doc = a.parse_processed_document({"doc_key": value["documentID"], "sentences": sentences}, include_gold=False)
    projection.require(a.inference_projection(doc) == value, "REQUEST_SOURCE_PROJECTION")
    return doc


def verify_manifest() -> dict:
    """Verify both materialized views and their gold-blind provenance before gold access."""
    manifest = runner.read(MANIFEST)
    for item in manifest["bindings"] + manifest["projections"]:
        verify(item)
    for item in runner.read(EVIDENCE)["files"]:
        verify(item)
    return manifest


def materialize() -> dict:
    """Read all original responses, not gold; fix/hash A and B before scoring is possible."""
    if MANIFEST.exists():
        return verify_manifest()
    projection.require(AMENDMENT.exists(), "AMENDMENT_REQUIRED_BEFORE_PROJECTION")
    projection.require(a.sha256_bytes(runner.CANDIDATE.read_bytes()) == runner.CANDIDATE_SHA, "CANDIDATE_IDENTITY")
    candidate = runner.read(runner.CANDIDATE)
    identity = runner.read(runner.ROOT / "identity.json")
    acceptance = runner.read(runner.APPROVALS / "runtime_acceptance.json")
    authorization = runner.read(runner.APPROVALS / "live_authorization.json")
    runner.check_approvals(candidate, runner.ROOT, acceptance, authorization)
    projection.require(identity == {"binding": runner.binding(candidate,runner.ROOT), "acceptance": acceptance, "authorization": authorization}, "RUN_IDENTITY")
    original_summary = runner.read(runner.ROOT / "summary.json")
    projection.require(original_summary["counts"] == {"successful":98,"failed_uncertain":2,"not_started":0} and original_summary["completedTraversal"], "ORIGINAL_TRAVERSAL")
    paths = []
    for root in (runner.ROOT, runner.APPROVALS, s.RUNTIME_ROOT, a.RUNTIME_ROOT / "approvals/single_dev_smoke_v0.1.0"):
        paths.extend(p for p in root.rglob("*") if p.is_file())
    paths += [a.SOURCE_FREEZE_PATH, a.ADAPTER_FREEZE_PATH, a.PROMPT_PATH, a.CONFIG_PATH, runner.CANDIDATE,
              s.PLAN_PATH, Path(a.__file__), Path(runner.__file__), Path(s.__file__)]
    snapshot = [evidence(p) for p in sorted(set(paths))]
    view_a=[]; view_b=[]; records=[]; ledger=[]; valid_count=0
    for entry, summary_row in zip(candidate["requests"], original_summary["documents"]):
        doc_id = entry["documentID"]; root = runner.document_root(runner.ROOT, doc_id)
        request = (root / "provider_request.json").read_bytes()
        projection.require(a.sha256_bytes(request) == entry["providerRequestBodySha256"], "REQUEST_HASH")
        document = source_document(s._strict_json(request))
        projection.require(document.document_id == doc_id == summary_row["documentID"], "DOCUMENT_ID")
        raw = (root / "raw_model_output.bin").read_bytes()
        response = runner.read(root / "provider_response.bin")
        projection.require(response == runner.read(root / "provider_response.json") and extract_model_output(response) == raw, "PROVIDER_OUTPUT_PARITY")
        validate_provider_response(response)
        terminal = runner.read(root / "terminal.json")
        projection.require(terminal["httpStatus"] == 200 and terminal["bodySha256"] == entry["providerRequestBodySha256"]
                           and terminal["terminalStatus"] == summary_row["terminalStatus"], "TERMINAL_PARITY")
        original = s._strict_json(raw)
        retained, rejections = projection.project(raw, document)
        if terminal["terminalStatus"] == "completed_valid":
            projection.require(not rejections and a.canonical_json(retained) == a.canonical_json(original)
                               == a.canonical_json(runner.read(root / "validated_prediction.json")), "VALID_DOCUMENT_CHANGED")
            sensitivity = original; valid_count += 1
        else:
            projection.require(terminal["failureCode"] == projection.REASON and bool(rejections), "OTHER_ORIGINAL_FAILURE")
            sensitivity = {"documentID":doc_id, "entities":[], "relations":[]}
        a.validate_prediction(sensitivity, document)
        for kind, id_key in (("entities","entityID"),("relations","relationID")):
            kept = {row[id_key] for row in retained[kind]}
            projection.require(retained[kind] == [row for row in original[kind] if row[id_key] in kept], "RETAINED_VALUES_OR_ORDER_CHANGED")
        view_a.append(retained); view_b.append(sensitivity); ledger.extend(rejections)
        records.append({"documentID":doc_id, "sourceOutput":evidence(root / "raw_model_output.bin"),
                        "request":evidence(root / "provider_request.json"), "originalStatus":terminal["terminalStatus"],
                        "originalCounts":{k:len(original[k]) for k in ("entities","relations")},
                        "retainedCountsA":{k:len(retained[k]) for k in ("entities","relations")},
                        "excludedCountsA":{k:len(original[k])-len(retained[k]) for k in ("entities","relations")},
                        "retainedCountsB":{k:len(sensitivity[k]) for k in ("entities","relations")},
                        "canonicalPredictionEquality":retained==original, "retainedValuesAndOrderEqual":True,
                        "projectionASha256":a.sha256_bytes(a.canonical_json(retained)),
                        "projectionBSha256":a.sha256_bytes(a.canonical_json(sensitivity))})
    projection.require(len(view_a)==len(view_b)==len({p["documentID"] for p in view_a})==100 and valid_count==98, "COMPLETE_100_REQUIRED")
    for item in snapshot: verify(item)
    write(A_PATH, b"".join(a.canonical_json(row)+b"\n" for row in view_a))
    write(B_PATH, b"".join(a.canonical_json(row)+b"\n" for row in view_b))
    write(LEDGER, encode({"version":"0.1.0", "policy":"post-run A", "rejections":ledger}))
    write(EVIDENCE, encode({"files":snapshot, "authenticBytesUnchanged":True}))
    manifest = {"version":"0.1.0", "materializedBeforeGoldAt":s._utc(), "goldAccessed":False,
                "policyA":"post-run record isolation", "policyB":"post-run document-rejection sensitivity",
                "predeclared":False,"documentCount":100,"unchangedOriginallyValidDocuments":valid_count,
                "projections":[evidence(A_PATH),evidence(B_PATH)],
                "bindings":[evidence(p) for p in (AMENDMENT,DECISIONS,LEDGER,EVIDENCE,Path(__file__),Path(projection.__file__))],
                "documents":records,"newProviderCalls":0}
    write(MANIFEST,encode(manifest))
    return manifest


def score() -> dict:
    """Only after fixed projections exist, load all frozen test gold and score both."""
    manifest = verify_manifest()  # No projection building/filtering after this boundary.
    candidate = runner.read(runner.CANDIDATE)
    predictions = [[s._strict_json(line) for line in p.read_bytes().splitlines()] for p in (A_PATH,B_PATH)]
    expected = [row["documentID"] for row in candidate["requests"]]
    for rows in predictions:
        projection.require([row["documentID"] for row in rows] == expected, "SCORING_MEMBERSHIP")
    authority = a.source_freeze()
    with a.ARCHIVE_PATH.open("rb") as handle:
        projection.require(a._sha256_stream(handle)==authority["officialArchive"]["sha256"], "GOLD_ARCHIVE_HASH")
    spec = authority["splits"]["test"]
    with tarfile.open(a.ARCHIVE_PATH,"r:gz") as archive:
        payload = archive.extractfile(spec["path"]).read()
    projection.require(a.sha256_bytes(payload)==spec["sha256"], "GOLD_SPLIT_HASH")
    gold = a.parse_processed_split(payload,include_gold=True)
    by_id = {doc.document_id:doc for doc in gold}
    projection.require(len(gold)==len(by_id)==100 and set(by_id)==set(expected), "COMPLETE_GOLD_REQUIRED")
    for doc in gold:
        record = next(row for row in candidate["requests"] if row["documentID"]==doc.document_id)
        projection.require(a.sha256_bytes(a.canonical_json(a.inference_projection(doc)))==record["projectionSha256"], "GOLD_SOURCE_PARITY")
    results = {label:a.score_documents((by_id[row["documentID"]],row) for row in rows)
               for label, rows in zip(("A_record_isolation","B_document_rejection_sensitivity"),predictions)}
    verify_manifest()
    report = {"version":"0.1.0", "scoredAt":s._utc(), "predeclared":False,
              "projectionManifest":evidence(MANIFEST), "goldSplit":spec,
              "unchangedScorer":evidence(Path(a.__file__)), "documentCountPerView":100,
              "results":results,"newProviderCalls":0,"step9Closed":False}
    write(OUT/"metrics.json",encode(report))
    return report


def main() -> None:
    """Expose two distinct offline phases; neither can dispatch or repair output."""
    parser=argparse.ArgumentParser(); parser.add_argument("phase",choices=("project","score"))
    args=parser.parse_args()
    result=materialize() if args.phase=="project" else score()
    print(json.dumps({"phase":args.phase,"documents":100,"newProviderCalls":0,
                      "results":result.get("results"),"unchangedOriginallyValidDocuments":result.get("unchangedOriginallyValidDocuments")}))


if __name__=="__main__":
    main()
