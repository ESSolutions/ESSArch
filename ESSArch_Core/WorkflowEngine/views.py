from django.http import Http404

from rest_framework.decorators import detail_route
from rest_framework.response import Response

from configuration.models import (
    Agent,
    EventType,
    Parameter,
    Path,
    Schema
)

from ip.models import (
    ArchivalInstitution,
    ArchivistOrganization,
    ArchivalType,
    ArchivalLocation,
    InformationPackage,
    EventIP
)

from preingest.models import (
    ProcessStep,
    ProcessTask,
)

from preingest.serializers import (
    ArchivalInstitutionSerializer,
    ArchivistOrganizationSerializer,
    ArchivalTypeSerializer,
    ArchivalLocationSerializer,
    InformationPackageSerializer,
    EventIPSerializer,
    EventTypeSerializer,
    ProcessStepSerializer,
    ProcessTaskSerializer,
    UserSerializer,
    GroupSerializer,
    SubmissionAgreementSerializer,
    ProfileSerializer,
    AgentSerializer,
    ParameterSerializer,
    PathSerializer,
    SchemaSerializer,
)

from profiles.models import (
    SubmissionAgreement,
    Profile,
    ProfileRel,
)

from django.contrib.auth.models import User, Group
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

class ArchivalInstitutionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows archival institutions to be viewed or edited.
    """
    queryset = ArchivalInstitution.objects.all()
    serializer_class = ArchivalInstitutionSerializer

class ArchivistOrganizationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows archivist organizations to be viewed or edited.
    """
    queryset = ArchivistOrganization.objects.all()
    serializer_class = ArchivistOrganizationSerializer

class ArchivalTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows archival types to be viewed or edited.
    """
    queryset = ArchivalType.objects.all()
    serializer_class = ArchivalTypeSerializer

class ArchivalLocationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows archival locations to be viewed or edited.
    """
    queryset = ArchivalLocation.objects.all()
    serializer_class = ArchivalLocationSerializer

class InformationPackageViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows information packages to be viewed or edited.
    """
    queryset = InformationPackage.objects.all()
    serializer_class = InformationPackageSerializer

    @detail_route()
    def prepare(self, request, pk=None):
        """
        Prepares the specified information package

        Args:
            pk: The primary key (id) of the information package to prepare

        Returns:
            None
        """
        try:
            InformationPackage.objects.get(pk=pk).prepare()
            return Response({'status': 'preparing ip'})
        except InformationPackage.DoesNotExist:
            raise Http404("Information package does not exist")


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

    @detail_route(methods=['put'], url_path='change-profile')
    def change_profile(self, request, pk=None):
        sa = SubmissionAgreement.objects.get(pk=pk)
        new_profile = Profile.objects.get(pk=request.data["new_profile"])
        old_profile = sa.profilerel_set.filter(
                profile__profile_type=new_profile.profile_type
        ).active()
        old_status = old_profile.get_sa_status(sa)

        if old_status == 1:
            old_profile.set_sa_status(sa, 0)

        if new_profile.get_sa_status(sa) != 2:
            ProfileRel.objects.update_or_create(
                submissionagreement=sa,
                profile=new_profile,
                defaults={
                    "status": 1
                },
            )

        return Response({
            'status': 'updating SA (%s) with new profile (%s)'.format(
                sa, new_profile
            )
        })

class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer

    @detail_route(methods=['post'])
    def save(self, request, pk=None):
        profile = Profile.objects.get(pk=pk)
        new_data = request.data["specification_data"]

        if (profile.specification_data.keys() == new_data.keys() and
                profile.specification_data != new_data):

            profile.copy_and_switch(
                submission_agreement=SubmissionAgreement.objects.get(
                    pk=request.data["submission_agreement"]
                ),
                specification_data=new_data,
                new_name=request.data["new_name"],
            )
            return Response({'status': 'saving profile'})

        return Response({'status': 'no changes, not saving'})

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
