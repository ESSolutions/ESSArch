import uuid

from countries_plus.models import Country
from django.db import models
from django.db.models import F
from django.utils.translation import ugettext_lazy as _
from languages_plus.models import Language


class AgentRelationType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)
    mirrored_type = models.ForeignKey('self', on_delete=models.PROTECT, null=True, verbose_name=_('mirrored type'))

    def __str__(self):
        return self.name


class AgentRelation(models.Model):
    agent_a = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='agent_relations_a')
    agent_b = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='agent_relations_b')
    type = models.ForeignKey('agents.AgentRelationType', on_delete=models.PROTECT, null=False)
    description = models.TextField(_('description'), blank=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)
    create_date = models.DateTimeField(_('create date'), auto_now_add=True)
    revise_date = models.DateTimeField(_('revise date'), auto_now=True)

    class Meta:
        unique_together = ('agent_a', 'agent_b', 'type')  # Avoid duplicates within same type


class Agent(models.Model):
    MINIMAL = 0
    PARTIAL = 1
    FULL = 2
    LEVEL_OF_DETAIL_CHOICES = (
        (MINIMAL, _('minimal')),
        (PARTIAL, _('partial')),
        (FULL, _('full')),
    )

    DRAFT = 0
    FINAL = 1
    RECORD_STATUS_CHOICES = (
        (DRAFT, _('draft')),
        (FINAL, _('final')),
    )

    LATIN = 0
    SCRIPT_CHOICES = (
        (LATIN, _('latin')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    places = models.ManyToManyField('agents.Topography', through='agents.AgentPlace', related_name='agents')
    type = models.ForeignKey('agents.AgentType', on_delete=models.PROTECT, null=False, related_name='agents')
    ref_code = models.ForeignKey('agents.RefCode', on_delete=models.PROTECT, null=False, related_name='agents')
    related_agents = models.ManyToManyField(
        'self',
        through='agents.AgentRelation',
        through_fields=('agent_a', 'agent_b'),
        symmetrical=False,
    )
    level_of_detail = models.IntegerField(
        _('level of detail'), choices=LEVEL_OF_DETAIL_CHOICES, null=False, db_index=True,
    )
    record_status = models.IntegerField(_('record status'), choices=RECORD_STATUS_CHOICES, null=False, db_index=True)
    script = models.IntegerField(_('script'), choices=SCRIPT_CHOICES, null=False, db_index=True)

    language = models.ForeignKey(Language, on_delete=models.PROTECT, null=False, verbose_name=_('language'))
    mandates = models.ManyToManyField('agents.SourcesOfAuthority', related_name='agents', verbose_name=_('mandates'))

    create_date = models.DateTimeField(_('create date'), null=False)
    revise_date = models.DateTimeField(_('revise date'), null=True)

    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)

    tags = models.ManyToManyField('tags.TagVersion', through='agents.AgentTagLink', related_name='agents')
    task = models.ForeignKey('WorkflowEngine.ProcessTask', on_delete=models.SET_NULL, null=True, related_name='agents')

    def __str__(self):
        name = self.names.order_by(F('start_date').asc(nulls_last=True)).last()
        if name is None:
            return super().__str__()

        return name.main


class AgentTagLink(models.Model):
    agent = models.ForeignKey(
        'agents.Agent',
        on_delete=models.CASCADE,
        null=False,
        related_name='tag_links',
        verbose_name=_('agent')
    )
    tag = models.ForeignKey(
        'tags.TagVersion',
        on_delete=models.CASCADE,
        null=False,
        related_name='agent_links',
        verbose_name=_('tag')
    )
    type = models.ForeignKey(
        'agents.AgentTagLinkRelationType',
        on_delete=models.PROTECT,
        null=False,
        verbose_name=_('type')
    )
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)
    description = models.TextField(_('description'), blank=True)


class AgentTagLinkRelationType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class AgentNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        'agents.Agent',
        on_delete=models.CASCADE,
        null=False,
        related_name='notes',
        verbose_name=_('agent')
    )
    type = models.ForeignKey('agents.AgentNoteType', on_delete=models.PROTECT, null=False, verbose_name=_('type'))
    text = models.TextField(_('text'), blank=False)
    href = models.TextField(_('href'), blank=True)
    create_date = models.DateTimeField(_('create date'), null=False)
    revise_date = models.DateTimeField(_('revise date'), null=True)


class AgentNoteType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class AgentFunction(models.Model):
    """
    TODO:
        1. figure out which fields to add
        2. add them
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, null=False, related_name='functions')


class SourcesOfAuthority(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.ForeignKey('agents.AuthorityType', on_delete=models.PROTECT, null=False)
    name = models.TextField(_('name'), blank=False)
    description = models.TextField(_('description'), blank=True)
    href = models.TextField(_('href'), blank=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)


class AuthorityType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class AgentIdentifier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identifier = models.TextField(_('identifier'), blank=False)
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, null=False, related_name='identifiers')
    type = models.ForeignKey('agents.AgentIdentifierType', on_delete=models.PROTECT, null=False, verbose_name=_('type'))


class AgentIdentifierType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class Topography(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=255)
    alt_name = models.TextField(_('alternative name'), blank=True)
    type = models.CharField(_('type'), max_length=255)
    main_category = models.TextField(_('main category'), blank=True)
    sub_category = models.TextField(_('sub category'), blank=True)
    reference_code = models.TextField(_('reference code'))
    start_year = models.DateField(_('start year'), null=True)
    end_year = models.DateField(_('end year'), null=True)
    lng = models.DecimalField(_('longitude'), max_digits=9, decimal_places=6, null=True)
    lat = models.DecimalField(_('latitude'), max_digits=9, decimal_places=6, null=True)

    class Meta:
        unique_together = ('name', 'type')  # Avoid duplicates within same type


class AgentPlaceType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class AgentPlace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, null=False)
    topography = models.ForeignKey('agents.Topography', on_delete=models.CASCADE, null=True)
    type = models.ForeignKey('agents.AgentPlaceType', on_delete=models.PROTECT, null=False)
    description = models.TextField(_('description'), blank=True)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)


class AgentType(models.Model):
    CORPORATE_BODY = 'corporatebody'
    PERSON = 'person'
    FAMILY = 'family'
    CPF_CHOICES = (
        (CORPORATE_BODY, _('corporate body')),
        (PERSON, _('person')),
        (FAMILY, _('family')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cpf = models.CharField(max_length=20, choices=CPF_CHOICES, blank=False, db_index=True)
    main_type = models.ForeignKey('agents.MainAgentType', on_delete=models.PROTECT, null=False)
    sub_type = models.TextField(_('sub type'), blank=True)
    legal_status = models.TextField(_('legal status'), blank=False)

    def __str__(self):
        if self.sub_type:
            return '{} - {}'.format(self.main_type.name, self.sub_type)

        return self.main_type.name


class MainAgentType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class AgentName(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, null=False, related_name='names')
    main = models.TextField(_('main'), blank=False)
    part = models.TextField(_('part'), blank=True)
    description = models.TextField(_('description'), blank=True)
    type = models.ForeignKey('agents.AgentNameType', on_delete=models.PROTECT, null=False)
    start_date = models.DateField(_('start date'), null=True)
    end_date = models.DateField(_('end date'), null=True)
    certainty = models.NullBooleanField(_('certainty'))


class AgentNameType(models.Model):
    name = models.CharField(_('name'), max_length=255, blank=False, unique=True)

    def __str__(self):
        return self.name


class RefCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        null=False,
        related_name='ref_codes',
        verbose_name=_('country code')
    )
    repository_code = models.CharField(_('repository code'), max_length=255, blank=False)

    def __str__(self):
        return '{}/{}'.format(self.country.iso, self.repository_code)

    class Meta:
        unique_together = ('country', 'repository_code')

