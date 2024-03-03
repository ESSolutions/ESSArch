import io

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
from ESSArch_Core.configuration.models import Feature
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.models import AppraisalJob
from ESSArch_Core.tags.models import Delivery, TagVersion
from ESSArch_Core.util import generate_file_response

User = get_user_model()


def get_data(user):
    ip_objs = InformationPackage.objects.for_user(user, [])
    data = {
        'appraisals': AppraisalJob.objects.filter(status=celery_states.SUCCESS).count(),
        'deliveries': Delivery.objects.for_user(user, []).count(),
        # 'information_packages': ip_objs.count(),
        # 'information_packages_sip': ip_objs.filter(package_type=0).count(),
        # 'information_packages_aic': ip_objs.filter(package_type=1).count(),
        'information_packages_aip': ip_objs.filter(package_type=2).count(),
        'ordered_information_packages': ip_objs.filter(orders__isnull=False).count(),
        'permissions': Permission.objects.count(),
        'roles': GroupMemberRole.objects.count(),
        # 'total_object_size': InformationPackage.objects.aggregate(Sum('object_size'))['object_size__sum'] or 0,
        'aip_object_size': ip_objs.filter(package_type=2).aggregate(Sum('object_size'))['object_size__sum'] or 0,
        'users': User.objects.count(),
    }

    if Feature.objects.filter(name='archival descriptions', enabled=True).exists():
        data['tags'] = list(TagVersion.objects.for_user(user, []).values(
            'type__name').annotate(total=Count('type')).order_by('type'))

    return data


@api_view()
@permission_classes((permissions.IsAuthenticated,))
def stats(request):
    user = request.user
    return Response(get_data(user))


@api_view()
@permission_classes((permissions.IsAuthenticated,))
def export(request):
    user = request.user
    data = get_data(user)

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
    f = io.BytesIO()

    ctype = 'application/pdf'
    render = render_to_string(template, {'data': data})
    HTML(string=render).write_pdf(f)

    f.seek(0)
    name = 'stats_{}.pdf'.format(timezone.now())
    return generate_file_response(f, content_type=ctype, name=name)
