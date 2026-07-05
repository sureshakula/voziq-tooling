"""cross_os — gap-registry cross-reference + non-mutating pre-flight runners."""

from aipass.aipass.apps.handlers.cross_os.gap_registry import (  # type: ignore[import-not-found]
    CrossOsGap,
    CrossOsGapError,
    find_gap_doc,
    gaps_for_platform,
    load_gaps,
    os_matches,
    parse_gap_registry,
)
from aipass.aipass.apps.handlers.cross_os.preflight import (  # type: ignore[import-not-found]
    PreflightResult,
    check_hookstatus,
    check_routing,
    check_versions,
    find_e2e_dir,
    run_e2e,
)
from aipass.aipass.apps.handlers.cross_os.run_record import (  # type: ignore[import-not-found]
    RunRecordError,
    build_run_record,
    default_record_path,
    generate_run_record,
)

__all__ = [
    "CrossOsGap",
    "CrossOsGapError",
    "PreflightResult",
    "RunRecordError",
    "build_run_record",
    "check_hookstatus",
    "check_routing",
    "check_versions",
    "default_record_path",
    "find_e2e_dir",
    "find_gap_doc",
    "gaps_for_platform",
    "generate_run_record",
    "load_gaps",
    "os_matches",
    "parse_gap_registry",
    "run_e2e",
]
