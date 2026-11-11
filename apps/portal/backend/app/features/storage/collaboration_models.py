"""Additive metadata for isolated team namespaces and upload-only inbox links."""
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.core.models import utcnow
from .native_models import identifier

class Team(Base):
    __tablename__='storage_teams'
    id:Mapped[str]=mapped_column(String(32),primary_key=True,default=identifier)
    owner_id:Mapped[int]=mapped_column(ForeignKey('users.id'),unique=True,index=True)
    root_id:Mapped[str]=mapped_column(ForeignKey('storage_nodes.id'),unique=True)
    name:Mapped[str]=mapped_column(String(120))
    created_at:Mapped[object]=mapped_column(DateTime,default=utcnow)

class TeamMember(Base):
    __tablename__='storage_team_members'
    id:Mapped[str]=mapped_column(String(32),primary_key=True,default=identifier)
    team_id:Mapped[str]=mapped_column(ForeignKey('storage_teams.id'),index=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    role:Mapped[str]=mapped_column(String(10))
    status:Mapped[str]=mapped_column(String(10),default='pending')
    invited_at:Mapped[object]=mapped_column(DateTime,default=utcnow)
    expires_at:Mapped[object]=mapped_column(DateTime)
    __table_args__=(UniqueConstraint('team_id','user_id'),)

class TeamUpload(Base):
    __tablename__='storage_team_uploads'
    upload_id:Mapped[str]=mapped_column(ForeignKey('storage_uploads.id'),primary_key=True)
    team_id:Mapped[str]=mapped_column(ForeignKey('storage_teams.id'),index=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'))

class FileRequest(Base):
    __tablename__='storage_file_requests'
    id:Mapped[str]=mapped_column(String(32),primary_key=True,default=identifier)
    owner_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    parent_id:Mapped[str|None]=mapped_column(ForeignKey('storage_nodes.id',ondelete='SET NULL'),nullable=True)
    title:Mapped[str]=mapped_column(String(120))
    token_hash:Mapped[str]=mapped_column(String(64),unique=True,index=True)
    max_file_size:Mapped[int]=mapped_column(BigInteger)
    max_total_size:Mapped[int]=mapped_column(BigInteger)
    created_at:Mapped[object]=mapped_column(DateTime,default=utcnow)
    expires_at:Mapped[object]=mapped_column(DateTime)
    closed_at:Mapped[object|None]=mapped_column(DateTime,nullable=True)

class RequestUpload(Base):
    __tablename__='storage_request_uploads'
    upload_id:Mapped[str]=mapped_column(ForeignKey('storage_uploads.id'),primary_key=True)
    request_id:Mapped[str]=mapped_column(ForeignKey('storage_file_requests.id'),index=True)
    created_at:Mapped[object]=mapped_column(DateTime,default=utcnow,index=True)
