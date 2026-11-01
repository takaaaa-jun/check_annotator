from datetime import UTC

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from app.models.comment import Comment
from app.models.group import Group
from app.models.role import Role
from app.models.state import State
from app.models.task import Task
from app.models.user import User


class ManagementRepository:
    def __init__(self, db: Session):
        self.db = db

    def _admin_reply_exists(self):
        reply, author, role = aliased(Comment), aliased(User), aliased(Role)
        return (select(reply.comment_id)
                .join(author, author.user_id == reply.user_id)
                .join(role, role.role_id == author.role_id)
                .where(reply.parent_id == Comment.comment_id,
                       reply.task_id == Comment.task_id,
                       reply.deleted_at.is_(None), author.deleted_at.is_(None),
                       role.deleted_at.is_(None), role.role_name == "admin")
                .correlate(Comment).exists())

    def _activity(self):
        author, owner, parent = aliased(User), aliased(User), aliased(Comment)
        author_role, owner_role = aliased(Role), aliased(Role)
        statement = (select(
            Comment, Task.image_id, Group.group_id, Group.group_name,
            owner.user_id.label("worker_id"), owner.user_name.label("worker_name"),
            author.user_name.label("user_name"), author_role.role_name.label("author_role"),
            parent.content.label("parent_content"), self._admin_reply_exists().label("has_admin_reply"))
            .join(Task, Task.task_id == Comment.task_id)
            .join(State, State.state_id == Task.state_id)
            .join(Group, Group.group_id == Task.group_id)
            .join(owner, owner.user_id == Group.user_id)
            .join(owner_role, owner_role.role_id == owner.role_id)
            .join(author, author.user_id == Comment.user_id)
            .join(author_role, author_role.role_id == author.role_id)
            .outerjoin(parent, and_(parent.comment_id == Comment.parent_id,
                                   parent.task_id == Comment.task_id, parent.deleted_at.is_(None)))
            .where(Comment.deleted_at.is_(None), Task.deleted_at.is_(None), State.deleted_at.is_(None),
                   Group.deleted_at.is_(None), owner.deleted_at.is_(None),
                   author.deleted_at.is_(None), author_role.deleted_at.is_(None),
                   owner_role.deleted_at.is_(None), owner_role.role_name != "admin"))
        return statement, author_role, owner

    def overview(self):
        workers = self.db.execute(select(User.user_id, User.user_name)
            .join(Role, Role.role_id == User.role_id)
            .where(User.deleted_at.is_(None), Role.deleted_at.is_(None), Role.role_name != "admin")
            .order_by(User.user_id)).all()
        states = self.db.scalars(select(State).where(State.deleted_at.is_(None)).order_by(State.state_id)).all()
        worker_ids = [row.user_id for row in workers]
        group_counts = dict(self.db.execute(select(Group.user_id, func.count(Group.group_id))
            .where(Group.user_id.in_(worker_ids), Group.deleted_at.is_(None)).group_by(Group.user_id)).all())
        counts = self.db.execute(select(Group.user_id, Task.state_id, func.count(Task.task_id))
            .join(Task, Task.group_id == Group.group_id).join(State, State.state_id == Task.state_id)
            .where(Group.user_id.in_(worker_ids), Group.deleted_at.is_(None),
                   Task.deleted_at.is_(None), State.deleted_at.is_(None))
            .group_by(Group.user_id, Task.state_id)).all()
        by_state = {(row[0], row[1]): row[2] for row in counts}
        activity, author_role, _ = self._activity()
        pending = activity.where(author_role.role_name != "admin", ~self._admin_reply_exists()).subquery()
        pending_counts = dict(self.db.execute(select(pending.c.worker_id, func.count())
            .group_by(pending.c.worker_id)).all())
        result = []
        for worker in workers:
            state_counts = [dict(state_id=state.state_id, state_name=state.state_name,
                                 count=by_state.get((worker.user_id, state.state_id), 0)) for state in states]
            result.append(dict(user_id=worker.user_id, user_name=worker.user_name,
                group_count=group_counts.get(worker.user_id, 0),
                total_count=sum(state["count"] for state in state_counts),
                completed_count=sum(state["count"] for state in state_counts if state["state_name"] == "完了"),
                pending_comments=pending_counts.get(worker.user_id, 0), state_counts=state_counts))
        return dict(workers=result, total_tasks=sum(row["total_count"] for row in result),
                    completed_tasks=sum(row["completed_count"] for row in result),
                    pending_comments=sum(row["pending_comments"] for row in result))

    def comments(self, page, page_size, worker_id=None, unanswered=False, replies_for=None):
        statement, author_role, owner = self._activity()
        if replies_for is not None:
            statement = statement.where(owner.user_id == replies_for, author_role.role_name == "admin", Comment.parent_id.is_not(None))
        else:
            statement = statement.where(author_role.role_name != "admin")
            if worker_id is not None:
                statement = statement.where(owner.user_id == worker_id)
            if unanswered:
                statement = statement.where(~self._admin_reply_exists())
        total = self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = self.db.execute(statement.order_by(Comment.created_at.desc(), Comment.comment_id.desc())
            .offset((page - 1) * page_size).limit(page_size)).all()
        result = []
        for row in rows:
            comment = row[0]
            result.append(dict(comment_id=comment.comment_id, task_id=comment.task_id,
                image_id=row.image_id, group_id=row.group_id, group_name=row.group_name,
                worker_id=row.worker_id, worker_name=row.worker_name,
                user_id=comment.user_id, user_name=row.user_name, author_role=row.author_role,
                parent_id=comment.parent_id, parent_content=row.parent_content, content=comment.content,
                created_at=comment.created_at.replace(tzinfo=UTC) if comment.created_at.tzinfo is None else comment.created_at.astimezone(UTC),
                updated_at=comment.updated_at.replace(tzinfo=UTC) if comment.updated_at.tzinfo is None else comment.updated_at.astimezone(UTC),
                has_admin_reply=bool(row.has_admin_reply)))
        return dict(comments=result, pagination=dict(page=page, page_size=page_size,
                    total=total, total_pages=(total + page_size - 1) // page_size))
