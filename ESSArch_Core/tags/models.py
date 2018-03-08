import uuid

from django.db import models, transaction
from django.db.models import F, OuterRef, Subquery
from django.utils import timezone
from mptt.models import MPTTModel, TreeForeignKey

from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.tags.documents import VersionedDocType


class Tag(MPTTModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    index = models.CharField(max_length=255, blank=False, default=None)
    link_id = models.UUIDField(default=uuid.uuid4)
    current_version = models.BooleanField(default=True)
    create_date = models.DateTimeField(auto_now_add=True)
    version_start_date = models.DateTimeField(null=True)
    version_end_date = models.DateTimeField(null=True)
    parent = TreeForeignKey('self', null=True, related_name='children', db_index=True)
    name = models.CharField('Name', max_length=255)
    type = models.CharField('Type', max_length=255)
    desc = models.CharField('Description', max_length=255, blank=True)
    information_packages = models.ManyToManyField(InformationPackage, related_name='tags')

    def to_search(self):
        d = {
            '_id': self.pk,
            '_index': self.index,
            'current_version': self.current_version,
            'name': self.name,
            'type': self.type,
        }

        return VersionedDocType(**d)

    def update_search(self, data, refresh=True):
        doc = self.to_search()
        doc.update(**data)

    def get_versions(self):
        return Tag.objects.filter(link_id=self.link_id).exclude(pk=self.pk)

    def create_new_version(self, start_date=None, end_date=None):
        """
        Creates a new version of the tag and all it's children. The new
        versions of the children will be related to the new version of
        the updated node.
        :param start_date: When the new version becomes active
        :type start_date: datetime.datetime | None
        :param end_date: When the new version becomes inactive
        :type end_date: datetime.datetime | None
        :return: The new version
        :rtype: ESSArch_Core.tags.models.Tag
        """

        branch = self.get_descendants(include_self=True)

        new_self = None
        new_ids = []

        with transaction.atomic():
            with Tag.objects.disable_mptt_updates():
                for tag in branch:
                    # create copies with same parent as old version
                    new = Tag(link_id=tag.link_id, index=tag.index, name=tag.name, type=tag.type, parent=tag.parent)
                    new.version_start_date = start_date
                    new.version_end_date = end_date

                    if start_date is not None and start_date <= timezone.now():
                        new.current_version = True
                        self.current_version = False
                    else:
                        new.current_version = False

                        self.save(update_fields=['current_version'])
                        new.save()

                    if new.link_id == self.link_id:
                        new_self = new

                    new_ids.append(str(new.pk))

                # set parent to latest version of all nodes except self

                old_parent = Tag.objects.filter(pk=OuterRef(OuterRef('parent')))
                latest_parent = Tag.objects.filter(link_id=Subquery(old_parent.values('link_id')[:1])).order_by('-create_date')

                # we can't use a bulk update because of a limitation in MySQL
                # that prevents the source and target table being the same
                #
                # "You cannot update a table and select from the same table
                # in a subquery."
                # - https://dev.mysql.com/doc/refman/5.7/en/update.html

                new_tags = Tag.objects.filter(pk__in=new_ids) \
                    .exclude(link_id=self.link_id) \
                    .annotate(parent_link_id=F('parent__link_id')) \
                    .annotate(latest_parent=Subquery(latest_parent.values('pk')[:1]))

                for new_tag in new_tags:
                    new_tag.parent_id = new_tag.latest_parent
                    new_tag.save()

            Tag.objects.partial_rebuild(self.tree_id)
            Tag.objects.partial_rebuild(new_self.tree_id)

        return new_self

    def set_as_current_version(self):
        with transaction.atomic():
            other_versions = self.get_versions().order_by('create_date')

            for version in other_versions:
                version.current_version = False
                version.save(update_fields=['current_version'])

            self.current_version = True
            self.save(update_fields=['current_version'])

    class Meta:
        permissions = (
            ('search', 'Can search'),
            ('view_pul', 'Can view PuL'),
        )

    def __unicode__(self):
        return self.name

    class MPTTMeta:
        order_insertion_by = ['name']
