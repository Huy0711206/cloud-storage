"""Filtering and locations for items already scoped to a personal workspace."""
from datetime import timedelta
from typing import Literal

from app.core.models import utcnow
from .native_models import FileNode
from .workspace_models import FileFavorite

FileKind = Literal["all", "folder", "image", "pdf", "video", "audio", "document"]


def filter_nodes(query, kind, modified_days, min_size):
    if kind == "folder":
        query = query.filter(FileNode.is_folder.is_(True))
    elif kind == "pdf":
        query = query.filter(FileNode.is_folder.is_(False), FileNode.mime_type == "application/pdf")
    elif kind == "document":
        mime = FileNode.mime_type
        query = query.filter(FileNode.is_folder.is_(False), (
            mime.like("text/%") | mime.like("application/vnd.openxmlformats-officedocument.%")
            | mime.in_(["application/msword", "application/vnd.ms-excel", "application/vnd.ms-powerpoint", "application/json"])
        ))
    elif kind != "all":
        query = query.filter(FileNode.is_folder.is_(False), FileNode.mime_type.like(f"{kind}/%"))
    if modified_days:
        query = query.filter(FileNode.modified_at >= utcnow() - timedelta(days=modified_days))
    if min_size is not None:
        query = query.filter(FileNode.is_folder.is_(False), FileNode.size >= min_size)
    return query


def parent_locations(db, owner_id, nodes):
    """Resolve the whole page one folder level at a time."""
    parents = {}
    frontier = {node.parent_id for node in nodes if node.parent_id}
    while frontier:
        rows = db.query(FileNode).filter(
            FileNode.owner_id == owner_id, FileNode.is_folder.is_(True),
            FileNode.deleted_at.is_(None), FileNode.id.in_(frontier),
        ).all()
        parents.update({row.id: row for row in rows})
        frontier = {row.parent_id for row in rows if row.parent_id and row.parent_id not in parents}

    locations = {}
    for node in nodes:
        path, seen = [], set()
        parent_id = node.parent_id
        while parent_id in parents and parent_id not in seen:
            parent = parents[parent_id]
            path.append({"id": parent.id, "name": parent.name})
            seen.add(parent.id)
            parent_id = parent.parent_id
        locations[node.id] = list(reversed(path))
    return locations


def set_favorite(db, user, node_id, starred):
    from .access import scope_guard, scoped_node
    with scope_guard(db, user) as (owner, team, _):
        node = scoped_node(db, owner, team, node_id)
        record = db.get(FileFavorite, (owner.id, node.id))
        if starred and record is None:
            db.add(FileFavorite(user_id=owner.id, node_id=node.id))
        elif not starred and record is not None:
            db.delete(record)
        db.commit()
    return {"starred": starred}
