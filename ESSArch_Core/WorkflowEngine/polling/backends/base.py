class BaseWorkflowPoller():
    def poll(self, path):
        raise NotImplementedError('subclasses of BaseWorkflowPoller must provide a poll() method')
