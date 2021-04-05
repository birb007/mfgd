from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from mfgd_app.models import Repository, UserProfile

# We require a valid, unique email
User._meta.get_field("email")._unique = True
User._meta.get_field("email").blank = False
User._meta.get_field("email").null = False

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(),validators=[validate_password])

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
        )

class RepoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(RepoForm, self).__init__(*args, **kwargs)
        self.fields["isPublic"].label = "Make repository public"

    class Meta:
        model = Repository
        fields = (
            "name",
            "path",
            "description",
            "isPublic",
        )

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email",)

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("image",)
