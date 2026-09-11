"""Human Annotation / Calibration Mode for Publication Pilot 1."""

INTERFACE_VERSION = "publication-pilot1-annotation-calibration/0.1.3"
ANNOTATION_OUTPUT_SCHEMA_VERSION = "0.1.2"
LEGACY_INTERFACE_VERSION = "publication-pilot1-annotation-calibration/0.1.2"
LEGACY_ANNOTATION_OUTPUT_SCHEMA_VERSION = "0.1.1"
GUIDELINE_VERSION = "0.1.1"
HANDBOOK_VERSION = "0.1.2"
HUMAN_CORE_GUIDE_VERSION = "1.1"
HUMAN_CORE_PRIMARY_ANNOTATOR_ID = "HUMAN_CORE_PRIMARY_RESEARCHER"
HUMAN_CORE_PRIMARY_SESSION_ID = "HUMAN_CORE_N5_PRIMARY_V1"
ROUTING_VERSION = "0.1.2"
CONTEXT_POLICY_NAME = "bounded_human_annotation_context"
CONTEXT_POLICY_VERSION = "0.1.0"


def metadata_versions(mode: str) -> tuple[str, str]:
    """Return the guide and handbook versions bound to one annotation mode."""

    if mode == "human-core":
        return HUMAN_CORE_GUIDE_VERSION, HUMAN_CORE_GUIDE_VERSION
    return GUIDELINE_VERSION, HANDBOOK_VERSION
