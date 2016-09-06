from django import forms

class AddTemplateForm(forms.Form):
    template_name = forms.CharField(max_length=50)
    file = forms.FileField()
