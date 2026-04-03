"""Portal adapters — each handles a specific job portal."""

from .base_adapter import BaseAdapter, FormField, ApplyResult, AdapterState
from .ssc_adapter import SSCAdapter
from .upsc_adapter import UPSCAdapter
from .linkedin_adapter import LinkedInAdapter
from .naukri_adapter import NaukriAdapter
from .indeed_adapter import IndeedAdapter
from .rrb_adapter import RRBAdapter
from .ibps_adapter import IBPSAdapter

__all__ = [
    "BaseAdapter", "FormField", "ApplyResult", "AdapterState",
    "SSCAdapter", "UPSCAdapter", "LinkedInAdapter", "NaukriAdapter",
    "IndeedAdapter", "RRBAdapter", "IBPSAdapter",
]

# Adapter registry
ADAPTER_REGISTRY = {
    "ssc": SSCAdapter,
    "upsc": UPSCAdapter,
    "linkedin": LinkedInAdapter,
    "naukri": NaukriAdapter,
    "indeed": IndeedAdapter,
    "rrb": RRBAdapter,
    "ibps": IBPSAdapter,
}
