"""Bounded supplementary matching report and unjudged, ignored review package."""

from collections import Counter
import io
import json
from pathlib import Path
import tarfile
import zipfile

from . import scierc_external_anchor as a
from . import scierc_overlap_matching as matching
from . import scierc_postrun_evaluation as prior
from . import scierc_smoke_runtime as s

ADDENDUM=a.PROJECT_ROOT / "docs/scierc_overlap_sensitivity_addendum_v0.1.0.md"
OUT=a.PROJECT_ROOT / "data/curation/papers/m2/scierc_overlap_sensitivity_v0.1.0"
REVIEW=a.RUNTIME_ROOT / "overlap_sensitivity_v0.1.0"


def item(doc, item_id: str, label: str, spans: list, **extra) -> dict:
    """Represent a scored item with source-derived argument text and sentence indices."""
    return {"id":item_id,"documentID":doc.document_id,"label":label,"spans":[list(span) for span in spans],
            "sentenceIndices":[a.sentence_for_span(*span,doc.sentence_ranges) for span in spans],
            "arguments":[{"span":list(span),"text":" ".join(doc.tokens[span[0]:span[1]+1])} for span in spans],**extra}


def inventories(doc, prediction: dict, layer: str) -> tuple:
    """Retain strict unique-signature supports, with original record IDs/variants."""
    if layer=="entity":
        predicted=[item(doc,e["entityID"],e["entityType"],[(e["spanStart"],e["spanEnd"])],nativeRecord=e) for e in prediction["entities"]]
        gold=[item(doc,"gold-entity-"+a.sha256_bytes(a.canonical_json(row)),row[2],[row[:2]]) for row in sorted(set(doc.gold_entities))]
    else:
        bound={e["entityID"]:e for e in prediction["entities"]}
        predicted=[]
        for relation in prediction["relations"]:
            ends=[bound[relation[key]] for key in ("sourceEntityID","targetEntityID")]
            predicted.append(item(doc,relation["relationID"],relation["relationType"],[(e["spanStart"],e["spanEnd"]) for e in ends],
                                  nativeRecord=relation,endpointEntityTypes=[e["entityType"] for e in ends]))
        variants={}
        for hs,he,ts,te,label in doc.gold_relations:
            key=a.relation_signature(label,(hs,he),(ts,te))
            variants.setdefault(key,[]).append((hs,he,ts,te,label))
        gold=[]
        for key,rows in sorted(variants.items()):
            representative=min(rows)
            spans=[representative[:2],representative[2:4]]
            types=[sorted({label for start,end,label in doc.gold_entities if (start,end)==span}) for span in spans]
            gold.append(item(doc,"gold-relation-"+a.sha256_bytes(a.canonical_json(key)),key[0],spans,
                             sourceAnnotationVariants=rows,endpointEntityTypes=types))
    return predicted,gold


def case_id(doc_id,layer,category,pred_id,gold_id) -> str:
    """Assign stable IDs independently of display ordering and source text."""
    return "case-"+a.sha256_bytes(a.canonical_json([doc_id,layer,category,pred_id,gold_id]))


def review_cases(doc,layer,predicted,gold,result) -> list:
    """Export every selected/alternative pair and unmatched item; judgments stay null."""
    ps={row["id"]:row for row in predicted}; gs={row["id"]:row for row in gold}; rows=[]
    def append(category,p=None,g=None,**extra):
        """Attach exact source sentence context to a review case."""
        sides=[table[key] for table,key in ((ps,p),(gs,g)) if key is not None]
        sentences=sorted({index for side in sides for index in side["sentenceIndices"]})
        context=[]
        for index in sentences:
            start,end=doc.sentence_ranges[index]
            context.append({"sentenceIndex":index,"span":[start,end],"text":" ".join(doc.tokens[start:end+1]),
                            "indexedTokens":[{"index":i,"text":doc.tokens[i]} for i in range(start,end+1)]})
        rows.append({"caseID":case_id(doc.document_id,layer,category,p,g),"documentID":doc.document_id,
                     "layer":layer,"category":category,"prediction":ps.get(p),"gold":gs.get(g),
                     "context":context,"semanticJudgment":None,"reviewerNotes":None,**extra})
    for p,g in result["locked"]: append("exact_locked",p,g,selected=True)
    selected=set(result["selected"])
    for (p,g),weight in sorted(result["eligible"].items()):
        alternatives=[case_id(doc.document_id,layer,"overlap_pair",x,y) for x,y in sorted(result["eligible"])
                      if (x,y)!=(p,g) and (x==p or y==g)]
        options=result["orientations"][p,g]
        append("overlap_pair",p,g,selected=(p,g) in selected,tokenIoU=str(weight),
               selectedOrientation=options[0][0] if (p,g) in selected else None,
               eligibleOrientations=[{"orientation":name,"meanIoU":str(score)} for name,score in options],
               competingAlternativeCaseIDs=alternatives,
               interpretation="mechanical correspondence only; unselected alternatives need not be globally co-optimal")
    for p in result["unmatchedPredictions"]: append("unmatched_prediction",p,selected=False)
    for g in result["unmatchedGold"]: append("unmatched_gold",g=g,selected=False)
    for p in sorted(ps):
        for g in sorted(gs):
            flags=matching.discrepancy_flags(ps[p],gs[g],layer)
            if flags: append("discrepancy_flags",p,g,flags=flags,selected=False)
    return rows


def metrics(tp: int,predictions: int,gold: int) -> dict:
    """Render unchanged micro arithmetic on unchanged supports."""
    return a._metrics({"TP":tp,"FP":predictions-tp,"FN":gold-tp,"goldSupport":gold,"predictionSupport":predictions})


def markdown_review(cases: list) -> str:
    """Readable review export with empty judgments and no inferred semantics."""
    lines=["# SciERC mechanical overlap review — unjudged", "",
           "All additional matches, eligible alternatives, exact locks, unmatched items and overlapping flags are included.",
           "These are not semantic equivalences, corrections, or new reference annotations. JSONL contains indexed tokens and full item records.",""]
    for row in cases:
        lines += [f'## {row["caseID"]}',"",f'{row["documentID"]} / {row["layer"]} / {row["category"]} / selected={row["selected"]}',""]
        for context in row["context"]:
            lines += [f'Sentence {context["sentenceIndex"]} {context["span"]}: '+json.dumps(context["text"],ensure_ascii=True),""]
        for side in ("prediction","gold"):
            value=row[side]
            lines += [side+": "+(json.dumps(value,ensure_ascii=True,sort_keys=True) if value else "null"),""]
        lines += ["Alternatives: "+json.dumps(row.get("competingAlternativeCaseIDs",[])),
                  "Orientations: "+json.dumps(row.get("eligibleOrientations",[])),
                  "Flags: "+json.dumps(row.get("flags",[])),"","Semantic judgment: ","Reviewer notes: ",""]
    return "\n".join(lines)


def render_report(report: dict) -> str:
    """Render all aggregate comparisons without source context."""
    lines=["# SciERC boundary-overlap sensitivity v0.1.0", "",
           "Supplementary post-run analysis, not predeclared confirmatory evaluation or improved extraction.",
           "Overlap pairs are mechanical correspondences, NOT human-validated semantic equivalences.",
           "Original A/B metrics, evidence, configuration and decisions remain unchanged. Step 9 remains open.","",
           "| Layer/view | TP | FP | FN | Gold | Predictions | Micro P | Micro R | Micro F1 | Additional |",
           "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for layer in ("entity","relation"):
        for view in ("strictA","overlapSensitivity"):
            row=report["metrics"][layer][view]
            lines.append(f'| {layer}/{view} | {row["TP"]} | {row["FP"]} | {row["FN"]} | {row["goldSupport"]} | {row["predictionSupport"]} | {row["precision"]:.6f} | {row["recall"]:.6f} | {row["f1"]:.6f} | {row["TP"]-report["metrics"][layer]["strictA"]["TP"]} |')
    lines += ["","## Nonexclusive discrepancy flags", "",json.dumps(report["discrepancyCounts"],indent=2),"",
              "Counts are prediction/gold pairs, not mutually exclusive error totals. Flags can involve already matched items.",
              "All selected additional pairs and all eligible residual alternatives are in the unjudged review export.",
              "Alternatives are not necessarily globally co-optimal. No semantic assessment or inferred adaptation prescription is supplied.","",
              "Rules and exact rational/lexical tie-break: `docs/scierc_overlap_sensitivity_addendum_v0.1.0.md`.",
              "Reproduce offline: `python -m src.extraction.llm.publications.scierc_overlap_analysis`.",
              "Ignored shareable ZIP: `var/scierc_external_anchor/overlap_sensitivity_v0.1.0/scierc_overlap_review_v0.1.0.zip`.",
              "No provider calls, thresholds searched, new reference annotations, or extraction changes.",""]
    return "\n".join(lines)


def main() -> None:
    """Compute one locked sensitivity from accepted A and complete frozen gold."""
    # Only directly needed accepted bindings are checked, not a historical runtime re-audit.
    projection_manifest=prior.runner.read(prior.MANIFEST)
    paths=[ADDENDUM,prior.MANIFEST,prior.OUT/"metrics.json",prior.A_PATH,prior.B_PATH,prior.DECISIONS,
           a.SOURCE_FREEZE_PATH,a.ADAPTER_FREEZE_PATH,Path(a.__file__),Path(matching.__file__),Path(__file__)]
    before=[prior.evidence(path) for path in paths]
    for value in projection_manifest["projections"]: prior.verify(value)
    old=prior.runner.read(prior.OUT/"metrics.json")
    prior.verify(old["projectionManifest"]); prior.verify(old["unchangedScorer"])
    prior.verify(next(row for row in projection_manifest["bindings"] if row["path"]==str(prior.DECISIONS.relative_to(a.PROJECT_ROOT))))
    predictions=[s._strict_json(line) for line in prior.A_PATH.read_bytes().splitlines()]
    authority=a.source_freeze()
    with a.ARCHIVE_PATH.open("rb") as stream:
        prior.projection.require(a._sha256_stream(stream)==authority["officialArchive"]["sha256"],"ARCHIVE_HASH")
    spec=authority["splits"]["test"]
    with tarfile.open(a.ARCHIVE_PATH,"r:gz") as archive: payload=archive.extractfile(spec["path"]).read()
    prior.projection.require(a.sha256_bytes(payload)==spec["sha256"],"TEST_HASH")
    documents=a.parse_processed_split(payload,include_gold=True); by_id={doc.document_id:doc for doc in documents}
    prior.projection.require(len(documents)==len(predictions)==len(by_id)==100 and {r["documentID"] for r in predictions}==set(by_id),"COMPLETE_MEMBERSHIP")
    counts={layer:Counter() for layer in ("entity","relation")}; cases=[]
    for prediction in predictions:
        doc=by_id[prediction["documentID"]]
        a.validate_prediction(prediction,doc)
        for layer in counts:
            predicted,gold=inventories(doc,prediction,layer)
            result=matching.match_layer(predicted,gold,layer)
            counts[layer].update(predictions=len(predicted),gold=len(gold),strict=len(result["locked"]),additional=len(result["selected"]))
            cases.extend(review_cases(doc,layer,predicted,gold,result))
    totals={}
    for layer,c in counts.items():
        strict=metrics(c["strict"],c["predictions"],c["gold"])
        prior.projection.require(strict==old["results"]["A_record_isolation"][layer],"STRICT_A_SUPPORT_OR_MATCH_DRIFT")
        totals[layer]={"strictA":strict,"overlapSensitivity":metrics(c["strict"]+c["additional"],c["predictions"],c["gold"]),"additionalMatches":c["additional"]}
    flags=Counter(flag for row in cases for flag in row.get("flags",[]))
    flags["entityFlaggedPairUnion"]=sum(row["category"]=="discrepancy_flags" and row["layer"]=="entity" for row in cases)
    flags["relationFlaggedPairUnion"]=sum(row["category"]=="discrepancy_flags" and row["layer"]=="relation" for row in cases)
    report={"version":"0.1.0","documentCount":100,"metrics":totals,"discrepancyCounts":dict(flags),
            "caseCounts":dict(Counter(row["category"] for row in cases)),"predeclared":False,
            "interpretation":"mechanical correspondences only, not semantic equivalences or improved extraction","newProviderCalls":0}
    assert len({row["caseID"] for row in cases})==len(cases)
    assert all(row["semanticJudgment"] is None and row["reviewerNotes"] is None for row in cases)
    context_files={"review.jsonl":b"".join(a.canonical_json(row)+b"\n" for row in cases),
                   "review.md":markdown_review(cases).encode(),"addendum.md":ADDENDUM.read_bytes(),
                   "aggregate_report.json":prior.encode(report)}
    package_manifest={"files":{name:{"sha256":a.sha256_bytes(raw),"sizeBytes":len(raw)} for name,raw in context_files.items()},
                      "semanticJudgments":"all empty","allAdditionalMatchesIncluded":True,"inputs":before}
    context_files["package_manifest.json"]=prior.encode(package_manifest)
    for name,raw in context_files.items(): prior.write(REVIEW/name,raw)
    zipped=io.BytesIO()
    with zipfile.ZipFile(zipped,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in sorted(context_files.items()):
            entry=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0)); entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,raw)
    zip_path=REVIEW/"scierc_overlap_review_v0.1.0.zip"; prior.write(zip_path,zipped.getvalue())
    for record in before: prior.verify(record)
    prior.write(OUT/"aggregate_report.json",prior.encode(report))
    prior.write(OUT/"manifest.json",prior.encode({"inputs":before,"goldSplit":spec,"allInputsUnchanged":True,
        "reviewArtifacts":[prior.evidence(REVIEW/name) for name in sorted(context_files)]+[prior.evidence(zip_path)],
        "aggregateReport":prior.evidence(OUT/"aggregate_report.json")}))
    prior.write(a.PROJECT_ROOT/"docs/scierc_overlap_sensitivity_report_v0.1.0.md",render_report(report).encode())
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
