from django.contrib import admin
from mfgd_app.models import UserProfile, Repository, CanAccess

class RepoAdmin(admin.ModelAdmin):
	list_display = ('name', 'description')

admin.site.register(UserProfile)
admin.site.register(Repository, RepoAdmin)
admin.site.register(CanAccess)