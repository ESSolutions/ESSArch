from rest_framework.decorators import detail_route
from rest_framework.response import Response

from preingest.models import (
    ProcessStep,
    ProcessTask,
)

from preingest.serializers import (
    ProcessStepSerializer,
    ProcessTaskSerializer,
    GroupSerializer,
    PermissionSerializer,
    UserSerializer,
)

from django.contrib.auth.models import User, Group, Permission
from rest_framework import viewsets

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

class PermissionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows permissions to be viewed or edited.
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer

class ProcessStepViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows steps to be viewed or edited.
    """
    queryset = ProcessStep.objects.all()
    serializer_class = ProcessStepSerializer

    @detail_route(methods=['post'])
    def run(self, request, pk=None):
        self.get_object().run()
        return Response({'status': 'running step'})

    @detail_route(methods=['post'])
    def continue_step(self, request, pk=None):
        step = self.get_object()
        task = step.tasks.first()
        step.waitForParams = False

        if request.method == "POST":
            for k, v in request.POST.iteritems():
                if k in task.params:
                    task.params[k] = v

            task.save()

        step.save()
        step.parent_step.run(continuing=True)
        return Response({'status': 'continuing step'})

    @detail_route(methods=['post'])
    def undo(self, request, pk=None):
        self.get_object().undo()
        return Response({'status': 'undoing step'})

    @detail_route(methods=['post'], url_path='undo-failed')
    def undo_failed(self, request, pk=None):
        self.get_object().undo(only_failed=True)
        return Response({'status': 'undoing failed tasks in step'})

    @detail_route(methods=['post'])
    def retry(self, request, pk=None):
        self.get_object().retry()
        return Response({'status': 'retrying step'})

class ProcessTaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tasks to be viewed or edited.
    """
    queryset = ProcessTask.objects.all()
    serializer_class = ProcessTaskSerializer

    @detail_route(methods=['post'])
    def undo(self, request, pk=None):
        self.get_object().undo()
        return Response({'status': 'undoing task'})

    @detail_route(methods=['post'])
    def retry(self, request, pk=None):
        self.get_object().retry()
        return Response({'status': 'retries task'})
