"""Offline Step 6A C1 production preflight; provider dispatch is injected only."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from src.extraction.llm.publications.authority_bundle import V015_SCHEMA013
from src.extraction.llm.publications.openai_provider import OpenAIProviderError, OpenAIHTTPError, OpenAIProviderResponseError, PROVIDER_NAME, REASONING_EFFORT, REQUESTED_MODEL, STORE, build_provider_input, build_responses_api_request
from src.extraction.llm.publications.production_acceptance import derive_accepted_semantic_projection, derive_unresolved_identity_sidecar, run_attempt_controller
from src.extraction.llm.publications.prospective_endpoint_binding_schema import derive_prospective_endpoint_binding_schema
from src.extraction.llm.publications.prospective_evidence_binding_schema import derive_prospective_evidence_binding_schema
from src.extraction.llm.publications.request_builder import PROJECT_ROOT, canonical_json, load_yaml_object, sha256_bytes
from src.extraction.llm.publications.run_publication_full_devset0_node_development import _downstream, _write_durable_canonical, _write_exact
from src.extraction.llm.publications.step5_freeze_materialization import _inputs

RUNNER_VERSION="publication-production-runner/0.1.1"; MAX_OUTPUT_TOKENS=32768; CONTEXT_BUDGET=1017232
_SCHEMA_CACHE: dict[tuple[str,...], dict[str,Any]] = {}
HUMAN_CORE_PATH=PROJECT_ROOT/"data/curation/papers/m2/human_core_gold/publication_human_core_gold_sample_freeze_v1.0.json"
N6_ENVELOPES_PATH=PROJECT_ROOT/"data/curation/papers/m2/step5_freeze/publication_pool_n6_c1_evaluation_envelopes_freeze_v0.1.1.json"
class ProductionPreflightError(ValueError): """Frozen production authority drift."""

def _load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text());
    if not isinstance(value,dict): raise ProductionPreflightError(f"not object: {path}")
    return value
def _context(unit:Mapping[str,Any], inv:Mapping[str,Mapping[str,Any]])->list[dict[str,Any]]:
    return [dict(x) for x in sorted((x for x in inv.values() if x["sectionID"]==unit["sectionID"] and x["sourceUnitID"]!=unit["sourceUnitID"] and x.get("eligibility")=="eligible"),key=lambda x:str(x["sourceUnitID"]))]
def _targets(route:Mapping[str,Any], rows:Mapping[str,Mapping[str,Any]])->list[str]:
    routed=[*route["eligibleNodeOperationalTargetIDs"],*route["eligibleRelationOperationalTargetIDs"]]
    result=sorted({str(x) for x in routed if str(x) in rows and rows[str(x)].get("production_responsibility") in {"llm","hybrid"} and rows[str(x)].get("emission_mode") in {"llm_candidate","resolver_mediated_candidate"} and rows[str(x)].get("pilot_treatment") in {"extract_and_evaluate","extract_and_monitor"}})
    if not result: raise ProductionPreflightError(f"no production target: {route['sourceUnitID']}")
    return result
def _has_targets(route:Mapping[str,Any], rows:Mapping[str,Mapping[str,Any]])->bool:
    """Check eligibility without treating an excluded source unit as an error."""
    routed=[*route["eligibleNodeOperationalTargetIDs"],*route["eligibleRelationOperationalTargetIDs"]]
    return any(str(x) in rows and rows[str(x)].get("production_responsibility") in {"llm","hybrid"} and rows[str(x)].get("emission_mode") in {"llm_candidate","resolver_mediated_candidate"} and rows[str(x)].get("pilot_treatment") in {"extract_and_evaluate","extract_and_monitor"} for x in routed)
def _authority(profile:Mapping[str,Any])->dict[str,Any]:
    ont=PROJECT_ROOT/"src/ontology/ontology_spec.yaml"; schema=V015_SCHEMA013.candidate_schema_path
    return {"candidateSchema":{"path":str(schema.relative_to(PROJECT_ROOT)),"version":"0.1.3","sha256":sha256_bytes(schema.read_bytes())},"targetInventory":{"path":str(V015_SCHEMA013.target_inventory_path.relative_to(PROJECT_ROOT)),"profileID":profile["profile_id"],"version":str(profile["schema_version"]),"sha256":sha256_bytes(V015_SCHEMA013.target_inventory_path.read_bytes())},"ontology":{"path":str(ont.relative_to(PROJECT_ROOT)),"version":"0.1.5","specSha256":sha256_bytes(ont.read_bytes()),"validatedOwlSha256":profile["ontology"]["validated_owl_sha256"]},"sourceUnitContract":{"path":"docs/publication_source_unit_contract.md","version":"0.1.2","sha256":sha256_bytes((PROJECT_ROOT/"docs/publication_source_unit_contract.md").read_bytes())},"evidenceValidationContract":{"path":str(V015_SCHEMA013.evidence_contract_path.relative_to(PROJECT_ROOT)),"sha256":sha256_bytes(V015_SCHEMA013.evidence_contract_path.read_bytes())},"evaluationMatchingContract":{"path":str(V015_SCHEMA013.evaluation_contract_path.relative_to(PROJECT_ROOT)),"sha256":sha256_bytes(V015_SCHEMA013.evaluation_contract_path.read_bytes())}}
def _prepared_request(unit_id:str,inv:Mapping[str,Mapping[str,Any]],routing:Mapping[str,Mapping[str,Any]],*,frozen_n6:Mapping[str,Any]|None=None)->dict[str,Any]:
    profile=load_yaml_object(V015_SCHEMA013.target_inventory_path); rows={str(x["operational_id"]):x for x in [*profile["node_targets"],*profile["relation_targets"]]}; unit,route=inv.get(unit_id),routing.get(unit_id)
    if unit is None or route is None: raise ProductionPreflightError(f"missing unit/routing: {unit_id}")
    targets=_targets(route,rows); context=_context(unit,inv); prompt=V015_SCHEMA013.prompt_path.read_bytes()
    if frozen_n6 is not None: targets=list(frozen_n6["routedExtractAndEvaluateTargetIDs"])
    r={"requestSchemaVersion":"0.1.0","requestBuilderVersion":RUNNER_VERSION,"authorityBundleID":V015_SCHEMA013.identifier,"purpose":"publication_step5_c1_evaluation" if frozen_n6 else "publication_c1_production","runID":f"publication-step5-c1-evaluation/0.1.1/{unit_id}" if frozen_n6 else f"publication-c1-production/0.1.0/{unit_id}","sourcePublicationID":str(unit["paperID"]),"sourceArtifactID":unit["canonicalArtifactID"],"primarySourceUnitID":unit_id,"contextSourceUnitIDs":[x["sourceUnitID"] for x in context],"contextUnits":context,"requestScope":"complete_section","includedCompleteSection":True,"extractionChannel":"open_discovery","eligibleOperationalTargetIDs":targets,"sourceUnit":dict(unit),"deterministicEndpoints":[{"nodeID":unit["canonicalArtifactID"],"className":"Paper","artifactID":unit["canonicalArtifactID"]}],"acceptedLocalCandidateEndpoints":[],"deferredRecords":[],"deferredRecordIDs":[],"targetDefinitions":[dict(rows[x]) for x in targets],"prompt":{"path":str(V015_SCHEMA013.prompt_path.relative_to(PROJECT_ROOT)),"version":V015_SCHEMA013.prompt_version,"sha256":sha256_bytes(prompt),"text":prompt.decode()},"authorities":_authority(profile)}
    r["requestID"]=f"publication-c1-request-{sha256_bytes(canonical_json(r))[:20]}"; r["offlineResponseMetadata"]={"provider":PROVIDER_NAME,"modelName":REQUESTED_MODEL,"modelVersion":None,"generationParameters":{"maxOutputTokens":MAX_OUTPUT_TOKENS},"tokenUsage":{},"costUSD":None,"retryCount":0,"responseCreatedAt":None}; r["requestInputSha256"]=sha256_bytes(canonical_json(r))
    schema_key=tuple(targets)
    if schema_key not in _SCHEMA_CACHE:
        _SCHEMA_CACHE[schema_key]=derive_prospective_endpoint_binding_schema(r) if any(x.startswith("PUB-R-") for x in targets) else derive_prospective_evidence_binding_schema(r)
    schema=deepcopy(_SCHEMA_CACHE[schema_key]); provider_input=build_provider_input(r); body=build_responses_api_request(provider_input,model_authorable_schema=schema,max_output_tokens=MAX_OUTPUT_TOKENS)
    if body["max_output_tokens"]!=MAX_OUTPUT_TOKENS or body["model"]!=REQUESTED_MODEL or body["reasoning"]["effort"]!=REASONING_EFFORT or body["store"] is not STORE or "tools" in body or len(canonical_json(body))>CONTEXT_BUDGET: raise ProductionPreflightError(f"configuration/context drift: {unit_id}")
    return {"request":r,"schema":schema,"providerInput":provider_input,"body":body}
def _envelope(p:Mapping[str,Any])->dict[str,Any]:
    r,b,s=p["request"],p["body"],p["schema"]
    return {"primarySourceUnitID":r["primarySourceUnitID"],"contextSourceUnitIDs":r["contextSourceUnitIDs"],"routedExtractAndEvaluateTargetIDs":r["eligibleOperationalTargetIDs"],"maxOutputTokens":b["max_output_tokens"],"requestEnvelopeSha256":sha256_bytes(canonical_json({x:r[x] for x in ("authorityBundleID","runID","primarySourceUnitID","contextSourceUnitIDs","requestScope","includedCompleteSection","eligibleOperationalTargetIDs","prompt")})),"providerRequestBodySha256":sha256_bytes(canonical_json(b)),"modelAuthorableSchemaSha256":sha256_bytes(canonical_json(s))}
def derive_production_preflight()->dict[str,Any]:
    """Build every primary production request offline; Step 5 constrains N=6 only."""
    inv,routing=_inputs(); profile=load_yaml_object(V015_SCHEMA013.target_inventory_path); rows={str(x["operational_id"]):x for x in [*profile["node_targets"],*profile["relation_targets"]]}
    ids=sorted(x["sourceUnitID"] for x in inv.values() if x.get("eligibility")=="eligible" and x.get("recordType") in {"journal_article","book_chapter"} and _has_targets(routing[x["sourceUnitID"]],rows))
    n5=sorted(str(x["sourceUnitID"]) for x in _load(HUMAN_CORE_PATH)["selectedUnits"]); n6rows=_load(N6_ENVELOPES_PATH)["envelopes"]; n6map={str(x["primarySourceUnitID"]):x for x in n6rows}; n6=sorted(n6map)
    if not set(n5+n6)<=set(ids): raise ProductionPreflightError("N5/N6 outside primary production population")
    prepared={x:_prepared_request(x,inv,routing,frozen_n6=n6map.get(x)) for x in ids}
    checks=[]
    for x in n6:
        actual,expected=_envelope(prepared[x]),n6map[x]; checks.append({"primarySourceUnitID":x,"matched":all(actual[k]==expected.get(k) for k in actual),"publication46SameSectionContext":actual["contextSourceUnitIDs"] if x=="pub:46:sec:0006:unit:0001" else None})
    if not all(x["matched"] for x in checks) or next(x for x in checks if x["primarySourceUnitID"]=="pub:46:sec:0006:unit:0001")["publication46SameSectionContext"]!=["pub:46:sec:0006:unit:0002"]: raise ProductionPreflightError("frozen N=6 envelope reproduction drift")
    records=[{"primarySourceUnitID":x,"runID":p["request"]["runID"],"requestID":p["request"]["requestID"],"outputID":f"publication-c1-output-{p['request']['requestInputSha256'][:20]}","requestInputSha256":p["request"]["requestInputSha256"],"providerRequestBodySha256":sha256_bytes(canonical_json(p["body"])),"contextSourceUnitIDs":p["request"]["contextSourceUnitIDs"],"productionTargetIDs":p["request"]["eligibleOperationalTargetIDs"]} for x,p in prepared.items()]
    return {"runnerVersion":RUNNER_VERSION,"providerModelCalls":0,"c1Execution":False,"populationAuthority":{"count":len(records),"basis":"frozen eligible primary source-unit inventory (journal_article/book_chapter), unit routing, v0.1.5 production responsibility/emission authority; excludes nonprimary corrigendum"},"productionTargetRule":"routed targets with production_responsibility llm|hybrid, emission_mode llm_candidate|resolver_mediated_candidate, and pilot_treatment extract_and_evaluate|extract_and_monitor","productionConfiguration":{"model":REQUESTED_MODEL,"reasoningEffort":REASONING_EFFORT,"maxOutputTokens":MAX_OUTPUT_TOKENS,"store":STORE,"tools":"none","web":False,"externalRetrieval":False},"humanCoreN5PrimarySourceUnitIDs":n5,"complementaryN6PrimarySourceUnitIDs":n6,"n6FrozenEnvelopeReproduction":checks,"requests":records,"artifactLayout":{"root":"data/curation/papers/m2/production_c1/<runID>/<requestID>","attempts":"attempt-01|attempt-02/{lifecycle,provider_request,provider_response,raw_output,parser,validation,usable_pipeline_output}.json","selected":"attempt_selection.json","acceptedProjection":"accepted_semantic_projection.json","unresolvedIdentity":"unresolved_identity_sidecar.json","terminal":"terminal_processing_failure.json"}}
ProviderCall=Callable[[Mapping[str,Any],int],bytes|Mapping[str,Any]]
def execute_with_provider_fixture(p:Mapping[str,Any],call:ProviderCall,*,artifact_root:Path|None=None)->dict[str,Any]:
    """Inject a detailed provider fixture through the frozen Step 4 controller.

    Only provider transport exceptions become retryable API_ERROR records.  Parser,
    binding, validation, and runner exceptions intentionally escape fail-closed.
    """
    r,s,b=p["request"],p["schema"],p["body"]; base={"requestInputSha256":r["requestInputSha256"],"providerInputSha256":sha256_bytes(p["providerInput"]),"authorityBundleID":r["authorityBundleID"],"requestedModel":REQUESTED_MODEL,"reasoningEffort":REASONING_EFFORT,"maxOutputTokens":MAX_OUTPUT_TOKENS,"modelAuthorableSchemaSha256":sha256_bytes(canonical_json(s)),"provider":PROVIDER_NAME,"toolConfiguration":"none","store":STORE}
    def persist(path:Path,value:Mapping[str,Any])->None:
        if artifact_root is not None: _write_durable_canonical(path,value)
    def attempt(n:int)->dict[str,Any]:
        root=(artifact_root/f"attempt-{n:02d}") if artifact_root is not None else None
        if root is not None:
            persist(root/"provider_request.json",b)
            persist(root/"lifecycle.json",{**base,"attemptNumber":n,"status":"initiated","semanticResponseProduced":False})
        try:
            returned=call(deepcopy(b),MAX_OUTPUT_TOKENS)
        except (OpenAIHTTPError,OpenAIProviderResponseError,OpenAIProviderError) as exc:
            failure={"failureType":type(exc).__name__,"message":str(exc)}
            if isinstance(exc,OpenAIHTTPError): failure["providerMetadata"]=dict(exc.diagnostic)
            if isinstance(exc,OpenAIProviderResponseError):
                failure["providerResponse"]=dict(exc.response); failure["providerMetadata"]=dict(exc.response_record)
            out={**base,"attemptNumber":n,"status":"provider_failed","parserResult":{"parseStatus":"processing_failed","processingCode":"API_ERROR","error":str(exc)},"validation":{"envelopeStatus":"processing_failed","recordResults":[{"recordType":"processing_failure"}]},"usablePipelineOutput":{"candidateNodes":[],"candidateEdges":[]},"providerFailure":failure}
            if root is not None: persist(root/"lifecycle.json",out)
            return out
        if isinstance(returned,Mapping):
            raw=returned.get("rawOutput")
            if not isinstance(raw,bytes): raise TypeError("detailed fixture rawOutput must be bytes")
            provider_response=returned.get("providerResponse"); provider_metadata=returned.get("providerMetadata")
        elif isinstance(returned,bytes): raw=returned; provider_response=None; provider_metadata=None
        else: raise TypeError("provider fixture must return bytes or detailed mapping")
        if root is not None:
            _write_exact(root/"raw_model_output.json",raw)
            if isinstance(provider_response,Mapping): persist(root/"provider_response.json",provider_response)
            if isinstance(provider_metadata,Mapping): persist(root/"provider_metadata.json",provider_metadata)
        parser,parsed,validation,usable=_downstream(raw,r,endpoint_binding=True,evidence_binding=True)
        out={**base,"attemptNumber":n,"status":"processed","parserResult":parser,"validation":validation,"usablePipelineOutput":usable,"rawOutputSha256":sha256_bytes(raw),"providerResponseSha256":sha256_bytes(canonical_json(provider_response)) if isinstance(provider_response,Mapping) else None,"providerMetadataSha256":sha256_bytes(canonical_json(provider_metadata)) if isinstance(provider_metadata,Mapping) else None}
        if root is not None:
            persist(root/"parser_result.json",parser); persist(root/"validation_results.json",validation); persist(root/"usable_pipeline_output.json",usable); persist(root/"lifecycle.json",out)
            if parsed is not None: _write_exact(root/"parsed_candidate.json",parsed)
        return out
    selection=run_attempt_controller(attempt); result={"attemptSelection":selection}
    if artifact_root: persist(artifact_root/"attempt_selection.json",selection)
    if selection["selectedAttemptNumber"] is not None:
        result["acceptedSemanticProjection"]=derive_accepted_semantic_projection(selection,r); result["unresolvedIdentitySidecar"]=derive_unresolved_identity_sidecar(selection,r)
        if artifact_root: persist(artifact_root/"accepted_semantic_projection.json",result["acceptedSemanticProjection"]); persist(artifact_root/"unresolved_identity_sidecar.json",result["unresolvedIdentitySidecar"])
    return result
