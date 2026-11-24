"""Move or trash selected personal nodes using the single-node rules."""
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from . import native_service as storage
from .access import scope_guard, scoped_node


class BatchBody(BaseModel):
    action: Literal["move", "trash"]
    ids: list[Annotated[str, Field(min_length=1, max_length=32)]] = Field(
        min_length=1, max_length=500
    )
    parent_id: str | None


def apply_batch(db, actor, action, node_ids, parent_id):
    ids = list(dict.fromkeys(node_ids))
    results = {}
    nodes = {}
    roots_by_id = {}

    with scope_guard(db, actor, write=True) as (owner, team, _):
        for node_id in ids:
            try:
                nodes[node_id] = scoped_node(db, owner, team, node_id, mutable=True)
            except storage.StorageError as exc:
                results[node_id] = {"status": "failed", "message": exc.detail}

        for node_id, node in nodes.items():
            try:
                ancestors = storage.ancestor_nodes(db, owner.id, node.parent_id)
            except storage.StorageError as exc:
                results[node_id] = {"status": "failed", "message": exc.detail}
                continue
            roots_by_id[node_id] = next(
                (ancestor["id"] for ancestor in ancestors if ancestor["id"] in nodes),
                node_id,
            )

        for node_id, root_id in roots_by_id.items():
            if node_id != root_id:
                continue
            try:
                if action == "move":
                    storage._update_scoped_node(
                        db, owner, team, nodes[node_id], {"parent_id": parent_id}
                    )
                else:
                    storage._trash_scoped_node(db, nodes[node_id])
            except storage.StorageError as exc:
                results[node_id] = {"status": "failed", "message": exc.detail}
            else:
                db.flush()
                results[node_id] = {"status": "applied"}

        for node_id, root_id in roots_by_id.items():
            if node_id != root_id:
                root_result = results[root_id]
                results[node_id] = (
                    {"status": "covered"}
                    if root_result["status"] == "applied"
                    else root_result
                )
        db.commit()

    return {"items": [{"id": node_id, **results[node_id]} for node_id in ids]}
