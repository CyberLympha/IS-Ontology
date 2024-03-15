from django import forms
from django.utils import timezone
from django.contrib.auth.models import User
from django.forms.widgets import HiddenInput
   
from IS_ontology.Notes.models import model_Note

class InputNoteForm(forms.ModelForm):
    class Meta:
        model = model_Note
        fields = ('title', 'obj', 'predicat', 'subj', 'status')

