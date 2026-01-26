from django.contrib import admin
from authentication.models import (
    UserModel,
    UserWhitelistTokenModel,
    TransactionModel
)

# Register your models here.
admin.site.register(UserModel)
admin.site.register(UserWhitelistTokenModel)
admin.site.register(TransactionModel)

