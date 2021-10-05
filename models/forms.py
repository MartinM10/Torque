from django import forms

from models.models import Sensor


class ExportForm(forms.ModelForm):
    id = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    user_full_name = forms.ModelMultipleChoiceField(label="Sensor",
                                                    widget=forms.SelectMultiple,
                                                    queryset=Sensor.objects.all().order_by('user_full_name'),
                                                    required=False)

    class Meta:
        model = Sensor
        fields = ['user_full_name']
