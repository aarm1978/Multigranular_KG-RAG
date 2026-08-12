(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ScreeningUIAids = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const rationaleTemplates = Object.freeze({
    "No semantic target": "No substantive scientific content relevant to the Publication Pilot 1 semantic targets; the unit contains [editorial metadata / administrative metadata / page furniture / other non-semantic material] only.",
    "Framing-focused": "Primarily research-framing content concerning [topic/problem/objective/significance], with routing limited to the framing and related semantic targets plausibly supported by the unit.",
    "Methods/data": "Primarily methods/data content describing [procedure/data/model/configuration], with routing focused on applicable method, entity, measurement-context, and study-context targets.",
    "Results": "Primarily results content reporting [findings/comparisons/metrics], with routing focused on findings, evaluation context, and applicable result-linked relations.",
    "Discussion/conclusion": "Primarily interpretive or synthesis content concerning [result interpretation/limitations/conclusions/future work], with routing focused on the corresponding discourse targets and explicit supported relation types.",
    "Study-area/geography": "Primarily study-area content identifying hydrologic features and/or named geographic areas relevant to the current study.",
    "Resource/software/data": "Primarily resource-oriented content concerning [dataset/model/tool/repository], with routing preserving use-versus-mention-versus-reference and exact-identity boundaries.",
    "Related work": "Primarily related-research content describing or comparing prior work, with routing limited to substantive prior-research semantics and explicit local connections authorized for Pilot 1.",
    "Mixed dense": "Semantically dense mixed content spanning [framing/methods/data/models/results/geography], with multiple target families and boundary distinctions likely to require later annotation.",
    "Mixed Introduction / Related Work": "Semantically dense introduction combining [research background/problem/current-study framing] with substantive prior research and named scientific resources, requiring careful current-study-versus-cited-study ownership and use-versus-mention routing.",
    "Genuinely ambiguous routing": "The unit supports prospective routing across [target/boundary A] and [target/boundary B], but the displayed text does not fully resolve the distinction; no external information was used."
  });

  function clearSemanticTargets(draft) {
    // Return a new draft with only route-like fields cleared. Density,
    // complexity, booleans, rationale, and notes remain explicit human choices.
    return {
      ...draft,
      routedNodeOperationalTargetIDs: [],
      routedRelationOperationalTargetIDs: [],
      likelyExhaustiveEmptyTargetIDs: [],
      likelyRecurringDistinctions: []
    };
  }

  function selectRationaleTemplate(existing, name, overwriteConfirmed) {
    // A blank selection never runs, and non-empty reviewer text requires an
    // affirmative confirmation supplied by the UI.
    if (!name || !Object.prototype.hasOwnProperty.call(rationaleTemplates, name)) {
      return { applied: false, value: existing };
    }
    if (String(existing).trim() && !overwriteConfirmed) {
      return { applied: false, value: existing };
    }
    return { applied: true, value: rationaleTemplates[name] };
  }

  return Object.freeze({ rationaleTemplates, clearSemanticTargets, selectRationaleTemplate });
});
