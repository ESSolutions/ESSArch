import os
import uuid

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template import loader

from rest_framework.decorators import detail_route, list_route
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from configuration.models import (
    Agent,
    EventType,
    Parameter,
    Path,
    Schema
)

from ip.models import (
    InformationPackage,
    EventIP
)

from preingest.models import (
    ProcessStep,
    ProcessTask,
)

from preingest.serializers import (
    InformationPackageSerializer,
    EventIPSerializer,
    EventTypeSerializer,
    ProcessStepSerializer,
    ProcessTaskSerializer,
    UserSerializer,
    GroupSerializer,
    SubmissionAgreementSerializer,
    ProfileTransferProjectSerializer,
    ProfileContentTypeSerializer,
    ProfileDataSelectionSerializer,
    ProfileClassificationSerializer,
    ProfileImportSerializer,
    ProfileSubmitDescriptionSerializer,
    ProfileSIPSerializer,
    ProfileAIPSerializer,
    ProfileDIPSerializer,
    ProfileWorkflowSerializer,
    ProfilePreservationMetadataSerializer,
    AgentSerializer,
    ParameterSerializer,
    PathSerializer,
    SchemaSerializer,
)

from profiles.models import (
    SubmissionAgreement,
    ProfileTransferProject,
    ProfileContentType,
    ProfileDataSelection,
    ProfileClassification,
    ProfileImport,
    ProfileSubmitDescription,
    ProfileSIP,
    ProfileAIP,
    ProfileDIP,
    ProfileWorkflow,
    ProfilePreservationMetadata,
)

from django.contrib.auth.models import User, Group
from rest_framework import viewsets

class JSONResponse(HttpResponse):
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)

def index(request):
    template = loader.get_template('preingest/index.html')
    context = {
        'steps' : Step.objects.all(),
        'tasks' : Task.objects.all()
    }
    return HttpResponse(template.render(context, request))

def run_step(request, name, *args, **kwargs):

    step = ProcessStep.objects.create_step_from_file(name)
    step.save()
    step.run()

    template = loader.get_template('preingest/run_step.html')

    context = {
        'step': step
    }

    return HttpResponse(template.render(context, request))

def continue_step(request, step_id, *args, **kwargs):

    step = ProcessStep.objects.get(id=step_id)
    task = step.tasks.first()
    step.waitForParams = False

    if request.method == "POST":
        for k, v in request.POST.iteritems():
            if k in task.params:
                task.params[k] = v

        task.save()

    step.save()
    step.parent_step.run(continuing=True)

    return redirect('history_detail', step_id=step.parent_step.id)

def run_task(request, name, *args, **kwargs):
    import importlib
    [module, task] = name.rsplit('.', 1)
    getattr(importlib.import_module(module), task)().delay()
    return HttpResponse("Running {}".format(name), request)

def steps(request, *args, **kwargs):
    steps = ProcessStep.objects.all()
    serializer = ProcessStepSerializer(steps, many=True)
    return JSONResponse(serializer.data)

def tasks(request, *args, **kwargs):
    tasks = ProcessTask.objects.all()
    serializer = ProcessTaskSerializer(tasks, many=True)
    return JSONResponse(serializer.data)

def history(request, *args, **kwargs):
    template = loader.get_template('preingest/history.html')

    context = {
        'steps': ProcessStep.objects.filter(parent_step__isnull=True)
    }

    return HttpResponse(template.render(context, request))

def history_detail(request, step_id, *args, **kwargs):
    template = loader.get_template('preingest/history_detail.html')

    context = {
        'step': ProcessStep.objects.get(id=step_id)
    }

    return HttpResponse(template.render(context, request))

def undo_failed(request, processstep_id, *args, **kwargs):
    step = ProcessStep.objects.get(id=processstep_id)
    step.undo(only_failed=True)
    return redirect('history_detail', step_id=processstep_id)

def undo_step(request, processstep_id, *args, **kwargs):
    step = ProcessStep.objects.get(id=processstep_id)
    step.undo()
    return redirect('history_detail', step_id=processstep_id)

def retry_step(request, processstep_id, *args, **kwargs):
    step = ProcessStep.objects.get(id=processstep_id)
    step.retry()
    return redirect('history_detail', step_id=processstep_id)

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

class InformationPackageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows information packages to be viewed or edited.
    """
    queryset = InformationPackage.objects.all()
    serializer_class = InformationPackageSerializer


class ProcessStepViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows steps to be viewed or edited.
    """
    queryset = ProcessStep.objects.all()
    serializer_class = ProcessStepSerializer

    @detail_route()
    def run(self, request, pk=None):
        self.get_object().run()
        return Response({'status': 'running step'})

    @detail_route()
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

    @detail_route()
    def undo(self, request, pk=None):
        self.get_object().undo()
        return Response({'status': 'undoing step'})

    @detail_route(url_path='undo-failed')
    def undo_failed(self, request, pk=None):
        self.get_object().undo(only_failed=True)
        return Response({'status': 'undoing failed tasks in step'})

    @detail_route()
    def retry(self, request, pk=None):
        self.get_object().retry()
        return Response({'status': 'retrying step'})

class ProcessTaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tasks to be viewed or edited.
    """
    queryset = ProcessTask.objects.all()
    serializer_class = ProcessTaskSerializer

class EventIPViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows events to be viewed or edited.
    """
    queryset = EventIP.objects.all()
    serializer_class = EventIPSerializer

class EventTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows event types to be viewed or edited.
    """
    queryset = EventType.objects.all()
    serializer_class = EventTypeSerializer

class SubmissionAgreementViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows submission agreements to be viewed or edited.
    """
    queryset = SubmissionAgreement.objects.all()
    serializer_class = SubmissionAgreementSerializer

class ProfileTransferProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = ProfileTransferProject.objects.all()
    serializer_class = ProfileTransferProjectSerializer

class ProfileContentTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = ProfileContentType.objects.all()
    serializer_class = ProfileContentTypeSerializer

class ProfileDataSelectionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = ProfileDataSelection.objects.all()
    serializer_class = ProfileDataSelectionSerializer

class ProfileClassificationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = ProfileClassification.objects.all()
    serializer_class = ProfileClassificationSerializer

class ProfileImportViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = ProfileImport.objects.all()
    serializer_class = ProfileImportSerializer

class ProfileSubmitDescriptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = ProfileSubmitDescription.objects.all()
    serializer_class = ProfileSubmitDescriptionSerializer

class ProfileSIPViewSet(viewsets.ModelViewSet):
    """
    API endpoi_class = ProfileSerializerat allows profiles to be viewed or edited.
    """
    queryset = ProfileSIP.objects.all()
    serializer_class = ProfileSIPSerializer

class ProfileAIPViewSet(viewsets.ModelViewSet):
    """
    API endpoi_class = ProfileSerializerat allows profiles to be viewed or edited.
    """
    queryset = ProfileAIP.objects.all()
    serializer_class = ProfileAIPSerializer

class ProfileDIPViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = ProfileDIP.objects.all()
    serializer_class = ProfileDIPSerializer

class ProfileWorkflowViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = ProfileWorkflow.objects.all()
    serializer_class = ProfileWorkflowSerializer

class ProfilePreservationMetadataViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = ProfilePreservationMetadata.objects.all()
    serializer_class = ProfilePreservationMetadataSerializer

class AgentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows agents to be viewed or edited.
    """
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer

class ParameterViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows parameters to be viewed or edited.
    """
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer

class PathViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows paths to be viewed or edited.
    """
    queryset = Path.objects.all()
    serializer_class = PathSerializer

class SchemaViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows schemas to be viewed or edited.
    """
    queryset = Schema.objects.all()
    serializer_class = SchemaSerializer
