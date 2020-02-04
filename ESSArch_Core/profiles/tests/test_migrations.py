from django_test_migrations.contrib.unittest_case import MigratorTestCase


class PolicyMoveFromInformationPackageToSubmissionAgreement(MigratorTestCase):
    migrate_from = ('profiles', '0053_submissionagreement_policy')
    migrate_to = ('profiles', '0055_non_nullable_sa_policy')

    def prepare(self):
        InformationPackage = self.old_state.apps.get_model('ip', 'InformationPackage')
        Path = self.old_state.apps.get_model('configuration', 'Path')
        StorageMethod = self.old_state.apps.get_model('storage', 'StorageMethod')
        StoragePolicy = self.old_state.apps.get_model('configuration', 'StoragePolicy')
        SubmissionAgreement = self.old_state.apps.get_model('profiles', 'SubmissionAgreement')

        sa = SubmissionAgreement.objects.create()
        policy = StoragePolicy.objects.create(
            policy_name='test',
            cache_storage=StorageMethod.objects.create(),
            ingest_path=Path.objects.create(),
        )
        InformationPackage.objects.create(submission_agreement=sa, policy=policy)

    def test_move_policy_to_submission_agreement(self):
        SubmissionAgreement = self.new_state.apps.get_model('profiles', 'SubmissionAgreement')

        sa = SubmissionAgreement.objects.get()
        self.assertEqual(sa.policy.policy_name, 'test')
