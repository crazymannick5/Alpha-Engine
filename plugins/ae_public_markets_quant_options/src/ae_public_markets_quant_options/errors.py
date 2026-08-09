class PmqoError(Exception):
    code = "PMQO_ERROR"


class IdentityAmbiguous(PmqoError):
    code = "PMQO_IDENTITY_AMBIGUOUS"


class IdentityNotFound(PmqoError):
    code = "PMQO_IDENTITY_NOT_FOUND"


class PointInTimeViolation(PmqoError):
    code = "PMQO_PIT_VIOLATION"


class LookaheadDetected(PmqoError):
    code = "PMQO_LOOKAHEAD_DETECTED"


class DataStale(PmqoError):
    code = "PMQO_DATA_STALE"


class ChainIncomplete(PmqoError):
    code = "PMQO_CHAIN_INCOMPLETE"


class DeliverableUnknown(PmqoError):
    code = "PMQO_DELIVERABLE_UNKNOWN"


class SourceRightsDenied(PmqoError):
    code = "PMQO_SOURCE_RIGHTS_DENIED"


class ResourceLimit(PmqoError):
    code = "PMQO_RESOURCE_LIMIT"


class CoreCapabilityRequired(PmqoError):
    code = "PMQO_CORE_CAPABILITY_REQUIRED"
