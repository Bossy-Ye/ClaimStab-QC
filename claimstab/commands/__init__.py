"""CLI command handlers."""

from .atlas import cmd_atlas_compare, cmd_export_dataset_registry, cmd_publish_result, cmd_validate_atlas
from .init_external_task import cmd_init_external_task
from .misc import cmd_examples, cmd_export_definitions
from .report import cmd_report
from .run import cmd_run
from .validate import cmd_validate_evidence, cmd_validate_spec

__all__ = [
    "cmd_atlas_compare",
    "cmd_examples",
    "cmd_export_dataset_registry",
    "cmd_export_definitions",
    "cmd_init_external_task",
    "cmd_publish_result",
    "cmd_report",
    "cmd_run",
    "cmd_validate_atlas",
    "cmd_validate_evidence",
    "cmd_validate_spec",
]
