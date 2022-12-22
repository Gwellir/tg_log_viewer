from django.contrib.auth.forms import AuthenticationForm

# from .models import LogUser
from django.contrib.auth.models import User


class LogUserLoginForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ('userame', 'password')

    def __init__(self, *args, **kwargs):
        super(LogUserLoginForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
