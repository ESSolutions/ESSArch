from countries_plus.models import Country
from django.db import models
from django.utils.translation import ugettext as _


class Language(models.Model):
    iso_639_1 = models.CharField(max_length=2, primary_key=True)
    iso_639_2T = models.CharField(max_length=3, unique=True, blank=True)
    iso_639_2B = models.CharField(max_length=3, unique=True, blank=True)
    iso_639_3 = models.CharField(max_length=3, blank=True)
    name_en = models.CharField(max_length=100)
    name_native = models.CharField(max_length=100)
    family = models.CharField(max_length=50)
    notes = models.CharField(max_length=100, blank=True)
    countries_spoken = models.ManyToManyField(Country, blank=True)

    class Meta:
        verbose_name = _('Language')
        verbose_name_plural = _('Languages')
        ordering = ['name_en']

    @property
    def iso(self):
        return self.iso_639_1

    @property
    def name(self):
        return self.name_native

    def __str__(self):
        return self.name_en
