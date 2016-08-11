from django import forms

from preingest.models import Profile

class PrepareSIPForm(forms.Form):
    meta_ArchivistOrganisation = forms.CharField(label="Archivist Organisation")
    meta_ArchivistOrganisationIdentity = forms.CharField(label="Archivist Organisation Identity")
    meta_ArchivistOrganisationSoftware = forms.CharField(label="Archivist Organisation Software")
    meta_ArchivistOrganisationSoftwareIdentity = forms.CharField(label="Archivist Organisation Software Identity")
    meta_CreatorOrganisation = forms.CharField(label="Creator Organisation")
    meta_CreatorOrganisationIdentity = forms.CharField(label="Creator Organisation Identity")
    meta_CreatorOrganisationSoftware = forms.CharField(label="Creator Organisation Software")
    meta_CreatorOrganisationSoftwareIdentity = forms.CharField(label="Creator Organisation Software Identity")
    meta_ProducerOrganisation = forms.CharField(label="Producer Organisation")
    meta_ProducerIndividual = forms.CharField(label="Producer Individual")
    meta_ProducerOrganisationSoftware = forms.CharField(label="Producer Organisation Software")
    meta_ProducerOrganisationSoftwareIdentity = forms.CharField(label="Producer Organisation Software Identity")
    meta_IpOwnerOrganisation = forms.CharField(label="IP Owner Organisation")
    meta_IpOwnerIndividual = forms.CharField(label="IP Owner Individual")
    meta_IpOwnerOrganisationSoftware = forms.CharField(label="IP Owner Organisation Software")
    meta_IpOwnerOrganisationSoftwareIdentity = forms.CharField(label="IP Owner Organisation Software Identity")
    meta_EditorOrganisation = forms.CharField(label="Editor Organisation")
    meta_EditorIndividual = forms.CharField(label="Editor Individual")
    meta_EditorOrganisationSoftware = forms.CharField(label="Editor Organisation Software")
    meta_EditorOrganisationSoftwareIdentity = forms.CharField(label="Editor Organisation Software Identity")
    meta_PreservationOrganisation = forms.CharField(label="Preservation Organisation")
    meta_PreservationIndividual = forms.CharField(label="Preservation Individual")
    meta_PreservationOrganisationSoftware = forms.CharField(label="Preservation Organisation Software")
    meta_PreservationOrganisationSoftwareIdentity = forms.CharField(label="Preservation Organisation Software Identity")

class CreateSIPForm(forms.Form):
    mets = forms.BooleanField(label="Include METS")
    premis = forms.BooleanField(label="Include PREMIS")

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = ['id']
