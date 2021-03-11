from django.contrib import admin
from mfgd_app.models import UserProfile, Repository, CanAccess

admin.site.register(UserProfile)
admin.site.register(Repository)
admin.site.register(CanAccess)
