from django.db import IntegrityError
from django.http import Http404

from rest_framework import status
from rest_framework.decorators import detail_route
from rest_framework.response import Response
from rest_framework.views import APIView

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
    InformationPackageDetailSerializer,
    EventIPSerializer,
    EventTypeSerializer,
    ProcessStepSerializer,
    ProcessTaskSerializer,
    UserSerializer,
    GroupSerializer,
    PermissionSerializer,
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
    ProfileLock,
    ProfileRel,
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

    def get_serializer_class(self):
        if self.action == 'list':
            return InformationPackageSerializer

        return InformationPackageDetailSerializer

    def create(self, request):
        """
        Prepares a new information package (IP) using the following tasks:

        1. Creates a new IP in the database.

        2. Creates a directory in the prepare directory with the name set to
        the id of the new IP.

        3. Creates an event in the database connected to the IP and with the
        detail "Prepare IP".

        Args:

        Returns:
            None
        """

        label = request.data.get('label', None)
        responsible = self.request.user.username or "Anonymous user"

        step = ProcessStep.objects.create(
            name="Prepare IP",
        )

        t1 = ProcessTask.objects.create(
            name="preingest.tasks.PrepareIP",
            params={
                "label": label,
                "responsible": responsible,
                "step": str(step.pk),
            },
            processstep_pos=0,
        )

        t2 = ProcessTask.objects.create(
            name="preingest.tasks.CreateIPRootDir",
            params={
            },
            result_params={
                "information_package_id": str(t1.pk)
            },
            processstep_pos=1,
        )

        t3 = ProcessTask.objects.create(
            name="preingest.tasks.CreateEvent",
            params={
                "detail": "Prepare IP",
            },
            result_params={
                "information_package_id": str(t1.pk)
            },
            processstep_pos=2,
        )

        step.tasks = [t1, t2, t3]
        step.save()
        step.run()

        return Response({"status": "Prepared IP"})

    @detail_route(methods=['post'])
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
            return Response(
                {'status': 'Information package with id %s does not exist' % pk},
                status=status.HTTP_404_NOT_FOUND
            )


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

        sa.change_profile(new_profile=new_profile)

        return Response({
            'status': 'updating SA (%s) with new profile (%s)' % (
                sa, new_profile
            )
        })

class ProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows profiles to be viewed or edited.
    """
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer

    def get_queryset(self):
        queryset = Profile.objects.all()
        profile_type = self.request.query_params.get('type', None)

        if profile_type is not None:
            queryset = queryset.filter(profile_type=profile_type)

        return queryset

    @detail_route(methods=['post'])
    def save(self, request, pk=None):
        profile = Profile.objects.get(pk=pk)
        new_data = request.data.get("specification_data", {})

        if (profile.specification_data.keys().sort() == new_data.keys().sort() and
                profile.specification_data != new_data):

            profile.copy_and_switch(
                submission_agreement=SubmissionAgreement.objects.get(
                    pk=request.data["submission_agreement"]
                ),
                specification_data=new_data,
                new_name=request.data["new_name"],
            )
            return Response({'status': 'saving profile'})

        return Response({'status': 'no changes, not saving'}, status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=["post"])
    def lock(self, request, pk=None):
        profile = Profile.objects.get(pk=pk)

        submission_agreement_id = request.data.get(
            "submission_agreement", {}
        )
        information_package_id = request.data.get(
            "information_package", {}
        )

        try:
            submission_agreement = SubmissionAgreement.objects.get(
                pk=submission_agreement_id
            )
        except SubmissionAgreement.DoesNotExist:
            return Response(
                {'status': 'Submission Agreement with id %s does not exist' % pk},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            information_package = InformationPackage.objects.get(
                pk=information_package_id
            )
        except InformationPackage.DoesNotExist:
            return Response(
                {'status': 'Submission Agreement with id %s does not exist' % pk},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            profile.lock(submission_agreement, information_package)
        except IntegrityError:
            exists = ProfileLock.objects.filter(
                submission_agreement=submission_agreement,
                information_package=information_package,
                profile=profile,
            ).exists

            if exists:
                return Response(
                    {'status': 'Lock already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )


        return Response({'status': 'locking profile'})

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
