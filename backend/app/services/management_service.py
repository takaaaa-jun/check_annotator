from app.core.exceptions import AuthenticationRequiredError, PermissionDeniedError
from app.repositories.management_repository import ManagementRepository
from app.repositories.user_repository import UserRepository


class ManagementService:
    def __init__(self, db):
        self.users = UserRepository(db)
        self.repository = ManagementRepository(db)

    def authorize(self, user_id, admin=False):
        user = self.users.find_active_by_id(user_id)
        if user is None or user.role.deleted_at is not None:
            raise AuthenticationRequiredError
        if admin and user.role.role_name != "admin":
            raise PermissionDeniedError

    def overview(self, user_id):
        self.authorize(user_id, admin=True)
        return self.repository.overview()

    def comments(self, user_id, page, page_size, worker_id=None, unanswered=False):
        self.authorize(user_id, admin=True)
        return self.repository.comments(page, page_size, worker_id, unanswered)

    def replies(self, user_id, page, page_size):
        self.authorize(user_id)
        return self.repository.comments(page, page_size, replies_for=user_id)
