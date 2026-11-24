"""Activity entries commit alongside successful team storage changes."""
from .access import team_access
from .workspace_models import TeamActivity


def record_activity(db, team, actor, action, node):
    if team is not None:
        db.add(TeamActivity(team_id=team.id, actor=actor.full_name, action=action, name=node.name))


def list_activity(db, user, team_id, before=None):
    team, _, _ = team_access(db, user, team_id)
    query = db.query(TeamActivity).filter_by(team_id=team.id)
    if before is not None:
        query = query.filter(TeamActivity.id < before)
    rows = query.order_by(TeamActivity.id.desc()).limit(31).all()
    return {
        "items": [
            {"id": row.id, "actor": row.actor, "action": row.action, "name": row.name,
             "created_at": row.created_at.isoformat() + "Z"}
            for row in rows[:30]
        ],
        "next_before": rows[29].id if len(rows) > 30 else None,
    }
