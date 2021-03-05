from django.db import models
from django.contrib.auth.models import User

class Repository(models.Model):
	name = models.CharField(max_length=256, unique=True, primary_key=True)
	description = models.TextField(blank=True)
	isPublic = models.BooleanField(default=False)

	class Meta:
		verbose_name_plural = 'Repositories'

	def __str__(self):
		return self.name

class UserProfile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)

	isAdmin = models.BooleanField(default=False)
	repositories = models.ManyToManyField(Repository, through='CanAccess')

	def __str__(self):
		return self.user.username

class CanAccess(models.Model):
	user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
	repo = models.ForeignKey(Repository, on_delete=models.CASCADE)

	canManage = models.BooleanField(default=False)

	class Meta:
		unique_together = [['user', 'repo']]
		verbose_name_plural = "CanAccess"

	def __str__(self):
		return f"{self.user}:{self.repo}"