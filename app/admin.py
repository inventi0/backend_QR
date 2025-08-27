from starlette_admin.contrib.sqla import Admin, ModelView
from .database import engine
from app.models.models import User

admin = Admin(engine, title="QR Admin")
admin.add_view(ModelView(User))
