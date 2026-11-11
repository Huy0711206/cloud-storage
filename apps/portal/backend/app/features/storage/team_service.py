"""Team access is explicit: member IDs never act as the sponsor on personal routes."""
from datetime import timedelta
from app.core.models import User,utcnow
from app.features.billing.entitlements import require_feature,benefits_for_user
from . import native_service as s
from .native_models import FileNode
from .collaboration_models import Team,TeamMember


# Compatibility names share the authoritative rules with every storage entrypoint.
from .access import (team_node_ids, assert_personal_node, team_access as access,
                     team_guard, team_node as scoped_node, fresh_user)


def serialize_team(db,team,sponsor,role):
    active=db.query(TeamMember).filter_by(team_id=team.id,status='active').count()+1
    return {'id':team.id,'name':team.name,'root_id':team.root_id,'owner_id':team.owner_id,'role':role,
            'writable':bool(benefits_for_user(sponsor).get('team_space')) and role in ('owner','editor'),
            'usage':s.quota_usage(db,sponsor),'member_count':active,'quota_policy':'shared_with_owner_personal'}


def list_teams(db,user):
    user=fresh_user(db,user.id)
    owned=db.query(Team).filter_by(owner_id=user.id).all()
    member_ids=[m.team_id for m in db.query(TeamMember).filter_by(user_id=user.id,status='active')]
    teams=owned+db.query(Team).filter(Team.id.in_(member_ids)).all()
    items=[]
    for team in teams:
        try:t,sponsor,role=access(db,user,team.id);items.append(serialize_team(db,t,sponsor,role))
        except s.StorageError:continue
    invitations=[]
    for member,team in db.query(TeamMember,Team).join(Team,TeamMember.team_id==Team.id).filter(TeamMember.user_id==user.id,TeamMember.status=='pending',TeamMember.expires_at>utcnow()).all():
        invitations.append({'id':member.id,'team_id':team.id,'team_name':team.name,'role':member.role})
    return {'items':items,'invitations':invitations}


def create_team(db,user,name):
    with s.owner_guard(db,user.id):
        user=fresh_user(db,user.id)
        require_feature(user,'team_space')
        if db.query(Team).filter_by(owner_id=user.id).first():raise s.StorageError(409,'Mỗi chủ gói có một không gian nhóm.')
        name=s.valid_name(name)
        if len(name)>120:raise s.StorageError(400,'Tên nhóm tối đa 120 ký tự.')
        # Internal root name has random identity and is hidden from personal browsing.
        root=FileNode(owner_id=user.id,name='Nhóm '+s.identifier(),is_folder=True)
        db.add(root);db.flush()
        team=Team(owner_id=user.id,root_id=root.id,name=name)
        db.add(team);db.commit()
        return serialize_team(db,team,user,'owner')


def members(db,user,team_id):
    team,owner,role=access(db,user,team_id)
    result=[{'id':'owner','user_id':owner.id,'email':owner.email,'full_name':owner.full_name,'role':'owner','status':'active'}]
    for member,person in db.query(TeamMember,User).join(User,TeamMember.user_id==User.id).filter(TeamMember.team_id==team_id).all():
        if member.status=='pending' and member.expires_at<=utcnow():continue
        result.append({'id':member.id,'user_id':person.id,'email':person.email,'full_name':person.full_name,'role':member.role,'status':member.status})
    return {'items':result}


def invite(db,user,team_id,email,role):
    if role not in ('editor','viewer'):raise s.StorageError(400,'Vai trò phải là người chỉnh sửa hoặc người xem.')
    with team_guard(db,user,team_id,True,True) as (team,owner,_):
        person=db.query(User).filter_by(email=email.strip().lower(),is_active=True,is_verified=True).first()
        if not person or person.id==owner.id:raise s.StorageError(400,'Hãy mời một tài khoản CloudBox đã xác minh khác.')
        existing=db.query(TeamMember).filter_by(team_id=team_id,user_id=person.id).first()
        if existing and (existing.status=='active' or existing.expires_at>utcnow()):raise s.StorageError(409,'Tài khoản đã là thành viên hoặc đang có lời mời.')
        occupied=db.query(TeamMember).filter(TeamMember.team_id==team_id,((TeamMember.status=='active')|((TeamMember.status=='pending')&(TeamMember.expires_at>utcnow())))).count()+1
        if occupied>=5:raise s.StorageError(409,'Nhóm tối đa 5 người, bao gồm chủ nhóm và lời mời đang chờ.')
        if not existing:existing=TeamMember(team_id=team_id,user_id=person.id,role=role);db.add(existing)
        existing.role=role;existing.status='pending';existing.invited_at=utcnow();existing.expires_at=utcnow()+timedelta(days=7)
        db.commit();return {'id':existing.id,'user_id':person.id,'role':role,'status':'pending'}


def accept_invitation(db,user,invitation_id):
    invite=db.query(TeamMember).filter_by(id=invitation_id,user_id=user.id,status='pending').first()
    if not invite:raise s.StorageError(404,'Không tìm thấy lời mời.')
    team=db.get(Team,invite.team_id)
    with s.owner_guard(db,team.owner_id,actor_id=user.id):
        user=fresh_user(db,user.id)
        invite=db.query(TeamMember).filter_by(id=invitation_id,user_id=user.id,status='pending').populate_existing().first()
        if not invite or invite.expires_at<=utcnow():raise s.StorageError(410,'Lời mời đã hết hạn.')
        owner=db.get(User,team.owner_id);require_feature(owner,'team_space')
        if db.query(TeamMember).filter_by(team_id=team.id,status='active').count()>=4:raise s.StorageError(409,'Nhóm đã đủ 5 thành viên.')
        if not user.is_active or not user.is_verified:raise s.StorageError(403,'Hãy xác minh tài khoản trước khi tham gia.')
        invite.status='active';db.commit()
        return serialize_team(db,team,owner,invite.role)


def change_member(db,user,team_id,user_id,role=None,remove=False):
    with team_guard(db,user,team_id,False,True):
        # Removing/changing members remains possible after expiry to contain access.
        if role is not None and role not in ('editor','viewer'):raise s.StorageError(400,'Vai trò không hợp lệ.')
        member=db.query(TeamMember).filter_by(team_id=team_id,user_id=user_id).first()
        if not member:raise s.StorageError(404,'Không tìm thấy thành viên.')
        if remove:db.delete(member)
        else:
            # Downgraded owner can reduce permissions but cannot grant edit privileges.
            if role=='editor':require_feature(db.get(User,user.id),'team_space')
            member.role=role
        db.commit();return {'ok':True}


def team_files(db,user,team_id,parent=None,q='',trash=False,offset=0,limit=200):
    team,owner,_=access(db,user,team_id)
    folder=scoped_node(db,team,parent)
    if not folder.is_folder:raise s.StorageError(400,'Hãy mở một thư mục.')
    # Scope first, then browse. Search is restricted to descendants of the team root.
    allowed={n.id for n in s.descendants(db,scoped_node(db,team),trash)}
    query=db.query(FileNode).filter(FileNode.id.in_(allowed),FileNode.id!=team.root_id)
    if trash:query=query.filter(FileNode.deleted_at.is_not(None),FileNode.trash_root_id==FileNode.id)
    else:
        query=query.filter(FileNode.deleted_at.is_(None))
        if not q:query=query.filter_by(parent_id=folder.id)
    if q:query=query.filter(FileNode.name.ilike('%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%',escape='\\'))
    offset=max(0,offset);limit=min(500,max(1,limit));count=query.count()
    rows=query.populate_existing().order_by(FileNode.is_folder.desc(),FileNode.name,FileNode.id).offset(offset).limit(limit).all()
    ancestors=[];cursor=folder
    while cursor.id!=team.root_id:
        ancestors.append({'id':cursor.id,'name':cursor.name});cursor=scoped_node(db,team,cursor.parent_id)
    return {'items':[s.serialize_node(n) for n in rows],'ancestors':list(reversed(ancestors)),'usage':s.quota_usage(db,owner),'root_id':team.root_id,'offset':offset,'limit':limit,'total_count':count,'has_more':offset+len(rows)<count,'next_offset':offset+len(rows) if offset+len(rows)<count else None}


def team_folder(db,user,team_id,name,parent=None):
    return s.create_folder(db,user,name,parent,team_id=team_id)


def team_change(db,user,team_id,node_id,changes):
    return s.update_node(db,user,node_id,changes,team_id=team_id)


def team_trash(db,user,team_id,node_id,restore=False):
    operation = s.restore_node if restore else s.trash_node
    return operation(db,user,node_id,team_id=team_id)


def team_upload(db,user,team_id,name,parent,size,replace_node_id=None):
    return s.start_upload(db,user,name,parent,size,replace_node_id,team_id=team_id)


def team_upload_action(db,user,team_id,upload_id,action,data=None,offset=None):
    if action=='chunk':return s.append_chunk(db,user,upload_id,data,offset,team_id=team_id)
    if action=='complete':return s.finish_upload(db,user,upload_id,team_id=team_id)
    return s.abort_upload(db,user,upload_id,team_id=team_id)
