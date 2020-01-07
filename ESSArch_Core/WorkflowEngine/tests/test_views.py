from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from groups_manager.models import GroupType
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from ESSArch_Core.auth.models import Group, GroupMember, GroupMemberRole
from ESSArch_Core.ip.models import InformationPackage
from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask
from ESSArch_Core.WorkflowEngine.serializers import (
    ProcessStepSerializer,
    ProcessTaskSerializer,
)

User = get_user_model()


class GetAllTasksTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('processtask-list')

        step = ProcessStep.objects.create()
        ProcessTask.objects.create(
            name="example.Foo",
            reference='first',
            processstep=step,
            args=[1],
            params={'bar': 'baz'},
            result='result from first',
        )
        ProcessTask.objects.create(
            name="example.Greet",
            reference='second',
            processstep=step,
            args=[2],
            params={'hello': 'world'},
            result='result from second',
        )
        ProcessTask.objects.create(
            name="example.HelloWorld",
            processstep=step,
            args=[3],
            params={'first_name': 'John', 'last_name': 'Smith'},
            result_params={
                'foo': 'first',
                'bar': 'second',
            },
        )

    def test_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        # get API response
        self.client.force_authenticate(user=self.user)
        request = APIRequestFactory().get(self.url)
        response = self.client.get(self.url)

        # get data from DB
        tasks = ProcessTask.objects.all()
        serializer = ProcessTaskSerializer(tasks, many=True, context={'request': request})

        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class GetAuthorizedTasksTests(TestCase):
    """
    Tasks that are connected to an IP must only be visible to
    users that can access the IP. If there are no IP connected
    then all users can see the task
    """

    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')

        self.org = Group.objects.create(name='organization', group_type=self.org_group_type)

        self.ip = InformationPackage.objects.create()
        self.org.add_object(self.ip)

        self.user_role = GroupMemberRole.objects.create(codename='user_role')
        perms = Permission.objects.filter(codename='view_informationpackage')
        self.user_role.permissions.set(perms)

        self.url = reverse('processtask-list')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_no_ip_connected(self):
        ProcessTask.objects.create(name="example.Foo", args=[1], params={'bar': 'baz'})
        response = self.client.get(self.url)
        request = APIRequestFactory().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tasks = ProcessTask.objects.all()
        serializer = ProcessTaskSerializer(tasks, many=True, context={'request': request})
        self.assertEqual(response.data, serializer.data)

    def test_user_in_organization(self):
        membership = GroupMember.objects.create(member=self.member, group=self.org)
        membership.roles.add(self.user_role)

        ProcessTask.objects.create(name="example.Foo", args=[1], params={'bar': 'baz'}, information_package=self.ip)
        response = self.client.get(self.url)
        request = APIRequestFactory().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tasks = ProcessTask.objects.all()
        serializer = ProcessTaskSerializer(tasks, many=True, context={'request': request})
        self.assertEqual(len(response.data), len(serializer.data))
        self.assertEqual(response.data, serializer.data)

    def test_user_not_in_organization(self):
        ProcessTask.objects.create(name="example.Foo", args=[1], params={'bar': 'baz'}, information_package=self.ip)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class CreateTaskTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('processtask-list')

        ProcessTask.objects.create(name="example.Foo", args=[1], params={'bar': 'baz'})
        ProcessTask.objects.create(name="example.Greet", args=[2], params={'hello': 'world'})
        ProcessTask.objects.create(name="example.HelloWorld", args=[3],
                                   params={'first_name': 'John', 'last_name': 'Smith'})

    def test_unauthenticated(self):
        response = self.client.post(self.url, {'name': 'example.Foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'example.Foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_permission(self):
        perm = Permission.objects.get(codename='add_processtask')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'example.Foo'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ChangeTaskTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')

        self.t1 = ProcessTask.objects.create(name="example.Foo", args=[1], params={'bar': 'baz'})
        self.t2 = ProcessTask.objects.create(name="example.Greet", args=[2], params={'hello': 'world'})
        self.t3 = ProcessTask.objects.create(name="example.HelloWorld", args=[3],
                                             params={'first_name': 'John', 'last_name': 'Smith'})

        self.url = reverse('processtask-detail', args=(self.t1.pk,))

    def test_unauthenticated(self):
        response = self.client.patch(self.url, {'name': 'example.Foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'name': 'example.Foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_permission(self):
        perm = Permission.objects.get(codename='change_processtask')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(self.url, {'name': 'new name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class GetAllStepsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('processstep-list')

        ProcessStep.objects.create(name="example.Foo")
        ProcessStep.objects.create(name="example.Greet")
        ProcessStep.objects.create(name="example.HelloWorld")

    def test_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        # get API response
        self.client.force_authenticate(user=self.user)
        request = APIRequestFactory().get(self.url)
        response = self.client.get(self.url)

        # get data from DB
        steps = ProcessStep.objects.all()
        serializer = ProcessStepSerializer(steps, many=True, context={'request': request})

        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class GetAuthorizedStepsTests(TestCase):
    """
    Steps that are connected to an IP must only be visible to
    users that can access the IP. If there are no IP connected
    then all users can see the step
    """

    def setUp(self):
        self.user = User.objects.create(username="admin")
        self.member = self.user.essauth_member
        self.org_group_type = GroupType.objects.create(label='organization')

        self.org = Group.objects.create(name='organization', group_type=self.org_group_type)

        self.ip = InformationPackage.objects.create()
        self.org.add_object(self.ip)

        self.user_role = GroupMemberRole.objects.create(codename='user_role')
        perms = Permission.objects.filter(codename='view_informationpackage')
        self.user_role.permissions.set(perms)

        self.url = reverse('processstep-list')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_no_ip_connected(self):
        ProcessStep.objects.create(name="example.Foo")
        response = self.client.get(self.url)
        request = APIRequestFactory().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        steps = ProcessStep.objects.all()
        serializer = ProcessStepSerializer(steps, many=True, context={'request': request})
        self.assertEqual(response.data, serializer.data)

    def test_user_in_organization(self):
        membership = GroupMember.objects.create(member=self.member, group=self.org)
        membership.roles.add(self.user_role)

        ProcessStep.objects.create(name="example.Foo", information_package=self.ip)
        response = self.client.get(self.url)
        request = APIRequestFactory().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        steps = ProcessStep.objects.all()
        serializer = ProcessStepSerializer(steps, many=True, context={'request': request})
        self.assertEqual(len(response.data), len(serializer.data))
        self.assertEqual(response.data, serializer.data)

    def test_user_not_in_organization(self):
        ProcessStep.objects.create(name="example.Foo", information_package=self.ip)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


class GetStepTasksTests(TestCase):
    def test_get_step_tasks(self):
        client = APIClient()
        user = User.objects.create(username='user')
        client.force_authenticate(user=user)

        step = ProcessStep.objects.create()
        task_in_step = ProcessTask.objects.create(processstep=step)
        ProcessTask.objects.create(name="task outside of step")

        url = reverse('steps-tasks-list', args=(step.pk,))
        response = client.get(url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(task_in_step.pk))


class CreateStepTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')
        self.url = reverse('processstep-list')

        ProcessStep.objects.create(name="example.Foo")
        ProcessStep.objects.create(name="example.Greet")
        ProcessStep.objects.create(name="example.HelloWorld")

    def test_unauthenticated(self):
        response = self.client.post(self.url, {'name': 'example.Foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'example.Foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_permission(self):
        perm = Permission.objects.get(codename='add_processstep')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {'name': 'example.Foo'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ChangeStepTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create(username='user')

        self.t1 = ProcessStep.objects.create(name="example.Foo")
        self.t2 = ProcessStep.objects.create(name="example.Greet")
        self.t3 = ProcessStep.objects.create(name="example.HelloWorld")

        self.url = reverse('processstep-detail', args=(self.t1.pk,))

    def test_unauthenticated(self):
        response = self.client.patch(self.url, {'name': 'example.Foo'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'name': 'example.Foo'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_with_permission(self):
        perm = Permission.objects.get(codename='change_processstep')
        self.user.user_permissions.add(perm)
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(self.url, {'name': 'new name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
