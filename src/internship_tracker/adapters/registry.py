from .generic import GenericAdapter
from .greenhouse import GreenhouseAdapter
from .icims import ICIMSAdapter
from .lever import LeverAdapter
from .smartrecruiters import SmartRecruitersAdapter
from .workday import WorkdayAdapter


def adapter_for(provider: str):
    return {
        "greenhouse": GreenhouseAdapter, "lever": LeverAdapter,
        "smartrecruiters": SmartRecruitersAdapter, "workday": WorkdayAdapter,
        "icims": ICIMSAdapter,
    }.get(provider, GenericAdapter)
