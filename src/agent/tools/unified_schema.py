"""
Deprecated compatibility shim for `src.agent.unified_schema`.

All canonical unified slot schema definitions now live in `src/agent/unified_schema.py`.
"""

import warnings

warnings.warn(
    "src.agent.tools.unified_schema is deprecated; import from src.agent.unified_schema instead.",
    DeprecationWarning,
    stacklevel=2,
)

from src.agent.unified_schema import (  # noqa: F401,E402
    UpdateSessionSlotsTool,
    apply_slot_updates,
    resolve_pending_confirmation,
)
