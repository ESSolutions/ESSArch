import tempfile

from celery import states as celery_states
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Count, Sum
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import exceptions, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from weasyprint import HTML

from ESSArch_Core.auth.models import GroupMemberRole
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.models import AppraisalJob
from ESSArch_Core.tags.models import TagVersion
from ESSArch_Core.util import generate_file_response

User = get_user_model()


def get_data():
    return {
        'appraisals': AppraisalJob.objects.filter(status=celery_states.SUCCESS).count(),
        'information_packages': InformationPackage.objects.count(),
        'ordered_information_packages': InformationPackage.objects.filter(orders__isnull=False).count(),
        'permissions': Permission.objects.count(),
        'roles': GroupMemberRole.objects.count(),
        'tags': list(TagVersion.objects.all().values('type__name').annotate(total=Count('type')).order_by('type')),
        'total_object_size': InformationPackage.objects.aggregate(Sum('object_size'))['object_size__sum'] or 0,
        'users': User.objects.count(),
    }


@api_view()
@permission_classes((permissions.IsAuthenticated,))
def stats(request):
    return Response(get_data())


@api_view()
@permission_classes((permissions.IsAuthenticated,))
def export(request):
    data = get_data()

    try:
        fields = request.query_params['fields'].split(',')
    except KeyError:
        fields = []

    if fields:
        try:
            data = {k: data[k] for k in fields}
        except KeyError as e:
            raise exceptions.ParseError('Unknown field: {}'.format(e))

    template = 'stats/export.html'.format()
    f = tempfile.TemporaryFile()

    ctype = 'application/pdf'
    render = render_to_string(template, {'data': data})
    HTML(string=render).write_pdf(f)

    f.seek(0)
    name = 'stats_{}.pdf'.format(timezone.now())
    return generate_file_response(f, content_type=ctype, name=name)
