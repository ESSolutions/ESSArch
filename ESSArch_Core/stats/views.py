from celery import states as celery_states
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Count, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from ESSArch_Core.auth.models import GroupMemberRole
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.maintenance.models import AppraisalJob
from ESSArch_Core.tags.models import TagVersion

User = get_user_model()


class StatsView(APIView):
    def get(self, request):
        data = {
            'appraisals': AppraisalJob.objects.filter(status=celery_states.SUCCESS).count(),
            'information_packages': InformationPackage.objects.count(),
            'ordered_information_packages': InformationPackage.objects.filter(orders__isnull=False).count(),
            'permissions': Permission.objects.count(),
            'roles': GroupMemberRole.objects.count(),
            'tags': TagVersion.objects.all().values('type').annotate(total=Count('type')).order_by('type'),
            'total_object_size': InformationPackage.objects.aggregate(Sum('object_size'))['object_size__sum'] or 0,
            'users': User.objects.count(),
        }

        return Response(data)
