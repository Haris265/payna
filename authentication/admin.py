from django.contrib import admin
from authentication.models import (
    UserModel,
    UserWhitelistTokenModel
)

# Register your models here.
admin.site.register(UserModel)
admin.site.register(UserWhitelistTokenModel)
