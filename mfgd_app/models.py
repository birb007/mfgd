from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Repository(models.Model):
    name = models.CharField(max_length=256, unique=True, primary_key=True)
    path = models.TextField(blank=True)
    description = models.TextField(blank=True)
    isPublic = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Repositories"

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.jpg', upload_to='profile_pics')

    isAdmin = models.BooleanField(default=False)
    repositories = models.ManyToManyField(Repository, through="CanAccess")

    def __str__(self):
        return self.user.username


class CanAccess(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)

    canManage = models.BooleanField(default=False)

    class Meta:
        unique_together = [["user", "repo"]]
        verbose_name_plural = "CanAccess"

    def __str__(self):
        return f"{self.user}:{self.repo}"
