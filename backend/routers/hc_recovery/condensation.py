"""
backend/routers/hc_recovery/condensation.py

STUB — this file did not exist in the uploaded project (only
backend/routers/hc_recovery/__init__.py was present), which meant
backend/main.py's unconditional
`from backend.routers.hc_recovery import feed, condensation, adsorption, membrane, compare`
crashed the whole app at import time — every unit page, not just
HC Recovery, was broken as a result.

This stub only restores boot: it registers the router so the app
starts and returns a clear 501 instead of a hard crash. The actual
HC Recovery request/response logic (reading simulation/hc_recovery/)
still needs to be written — treat this as a placeholder, not a
completed feature.
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/hc-recovery/condensation", include_in_schema=True, summary="Not yet implemented")
async def condensation_not_implemented():
    raise HTTPException(
        status_code=501,
        detail="HC Recovery 'condensation' endpoint is not yet implemented — this is a placeholder stub.",
    )
