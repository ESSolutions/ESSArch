from ESSArch_Core.maintenance.models import AppraisalJob, ConversionJob
from ESSArch_Core.WorkflowEngine.dbtask import DBTask


class RunAppraisalJob(DBTask):
    def run(self, pk):
        job = AppraisalJob.objects.get(pk=pk)
        return job.run()


class RunConversionJob(DBTask):
    def run(self, pk):
        job = ConversionJob.objects.get(pk=pk)
        return job.run()
