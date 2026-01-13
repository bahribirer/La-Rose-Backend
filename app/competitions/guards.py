from fastapi import HTTPException

async def require_competition_acceptance(db, user):
    from .service import get_current_competition, user_has_accepted

    competition = await get_current_competition()
    if not competition:
        raise HTTPException(
            status_code=403,
            detail="No active competition"
        )

    accepted = await user_has_accepted(
        db,
        competition["_id"],
        user["_id"]
    )

    if not accepted:
        raise HTTPException(
            status_code=403,
            detail="User not accepted into competition"
        )

    return competition
