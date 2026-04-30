from django import forms
from django.forms import inlineformset_factory

from .models import Compositor, Referencia


class CompositorForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()

        nascimento = (cleaned_data.get("nascimento") or "").strip()
        morte = (cleaned_data.get("morte") or "").strip()
        a_val = (cleaned_data.get("a") or "").strip()
        d_val = (cleaned_data.get("d") or "").strip()
        fl = (cleaned_data.get("fl") or "").strip()

        tem_nascimento_morte = bool(nascimento or morte)
        tem_a_d = bool(a_val or d_val)
        tem_fl = bool(fl)

        grupos_preenchidos = sum([tem_nascimento_morte, tem_a_d, tem_fl])
        if grupos_preenchidos > 1:
            raise forms.ValidationError(
                "Use apenas um formato cronológico: (nascimento/morte) ou (a./d.) ou (fl.)."
            )

        return cleaned_data

    class Meta:
        model = Compositor
        fields = [
            "apelido",
            "nome",
            "nascimento",
            "nascimento_c",
            "morte",
            "morte_c",
            "a",
            "d",
            "fl",
        ]
        labels = {
            "apelido": "Apelido",
            "nome": "Nome",
            "nascimento": "Nascimento",
            "nascimento_c": "Nascimento com circa (c.)",
            "morte": "Morte",
            "morte_c": "Morte com circa (c.)",
            "a": "a.",
            "d": "d.",
            "fl": "fl.",
        }
        widgets = {
            "apelido": forms.TextInput(attrs={"placeholder": "Ex: Bomtempo"}),
            "nome": forms.TextInput(attrs={"placeholder": "Ex: João Domingos"}),
            "nascimento": forms.TextInput(attrs={"placeholder": "Ex: 1775"}),
            "morte": forms.TextInput(attrs={"placeholder": "Ex: 1842"}),
            "a": forms.TextInput(attrs={"placeholder": "Ex: 1800"}),
            "d": forms.TextInput(attrs={"placeholder": "Ex: 1825"}),
            "fl": forms.TextInput(attrs={"placeholder": "Ex: sec. XVIII"}),
            "nascimento_c": forms.CheckboxInput(attrs={"style": "width:auto;"}),
            "morte_c": forms.CheckboxInput(attrs={"style": "width:auto;"}),
        }


class ReferenciaForm(forms.ModelForm):
    class Meta:
        model = Referencia
        fields = ["nome", "url"]
        labels = {
            "nome": "Nome",
            "url": "Link",
        }
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex: Biblioteca Nacional"}),
            "url": forms.URLInput(attrs={"placeholder": "https://..."}),
        }


ReferenciaFormSet = inlineformset_factory(
    Compositor,
    Referencia,
    form=ReferenciaForm,
    extra=1,
    can_delete=True,
)
