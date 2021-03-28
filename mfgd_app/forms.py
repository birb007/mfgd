from django import forms
from django.contrib.auth.models import User
from mfgd_app.models import Repository


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
        )

class RepoForm(forms.ModelForm):

	class Meta:
		model = Repository
		fields = (
			"name",
			"path",
			"description",
			"isPublic",
		)