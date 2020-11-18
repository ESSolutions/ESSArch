import importlib

from celery import states as celery_states
from django.db import transaction
from tenacity import retry, stop_after_delay, wait_random_exponential

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask


def get_result(step, reference):
    tasks = ProcessTask.objects.values_list('reference', 'result').filter(processstep=step, reference__isnull=False)
    results = dict((x, y) for x, y in tasks)

    if isinstance(reference, list):
        return [results[ref] for ref in reference]

    return results[reference]


def _create_on_error_tasks(errors, ip=None, responsible=None, eager=False, status=celery_states.PENDING):
    for on_error_idx, on_error in enumerate(errors):
        args = on_error.get('args', [])
        params = on_error.get('params', {})
        result_params = on_error.get('result_params', {})
        yield ProcessTask(
            name=on_error['name'],
            reference=on_error.get('reference', None),
            label=on_error.get('label'),
            hidden=on_error.get('hidden', False),
            args=args,
            params=params,
            result_params=result_params,
            eager=eager,
            information_package=ip,
            responsible=responsible,
            processstep_pos=on_error_idx,
            status=status,
        )


def _create_step(parent_step, flow, ip, responsible, context=None):
    if context is None:
        context = {}
    for e_idx, flow_entry in enumerate(flow):
        if not flow_entry.get('if', True):
            continue

        if flow_entry.get('step', False):
            if flow_entry.get('from') is not None:
                method = getattr(ip, flow_entry.get('from'))
                children = method()
            elif len(flow_entry.get('children', [])) > 0:
                children = flow_entry.get('children', [])
            else:
                # no child steps or tasks in step, no need to create step
                continue

            child_s = ProcessStep.objects.create(
                name=flow_entry['name'],
                parallel=flow_entry.get('parallel', False),
                parent_step=parent_step,
                parent_step_pos=e_idx,
                eager=parent_step.eager,
                information_package=ip,
                context=context,
            )

            on_error_tasks = list(_create_on_error_tasks(
                flow_entry.get('on_error', []), ip=ip, responsible=responsible,
                eager=parent_step.eager
            ))
            ProcessTask.objects.bulk_create(on_error_tasks)
            child_s.on_error.add(*on_error_tasks)

            _create_step(child_s, children, ip, responsible, context=context)
        else:
            name = flow_entry['name']

            [module, klass] = name.rsplit('.', 1)
            if not hasattr(importlib.import_module(module), klass):
                raise ValueError('Unknown task "{}"'.format(name))

            args = flow_entry.get('args', [])
            params = flow_entry.get('params', {})
            result_params = flow_entry.get('result_params', {})
            task = ProcessTask.objects.create(
                name=name,
                reference=flow_entry.get('reference', None),
                label=flow_entry.get('label'),
                args=args,
                params=params,
                result_params=result_params,
                eager=parent_step.eager,
                allow_failure=flow_entry.get('allow_failure', False),
                information_package=ip,
                responsible=responsible,
                processstep=parent_step,
                processstep_pos=e_idx,
                hidden=flow_entry.get('hidden', False),
                run_if=flow_entry.get('run_if', ''),
            )

            on_error_tasks = list(
                _create_on_error_tasks(flow_entry.get('on_error', []), ip=ip, responsible=responsible)
            )
            ProcessTask.objects.bulk_create(on_error_tasks)
            task.on_error.add(*on_error_tasks)


@retry(reraise=True, stop=stop_after_delay(30),
       wait=wait_random_exponential(multiplier=1, max=60))
def create_workflow(workflow_spec, ip=None, name='', on_error=None, eager=False, context=None):
    if on_error is None:
        on_error = []
    if context is None:
        context = {}
    responsible = getattr(ip, 'responsible', None)

    with transaction.atomic():
        with ProcessStep.objects.delay_mptt_updates():
            root_step = ProcessStep.objects.create(name=name, eager=eager, context=context)

            on_error_tasks = list(_create_on_error_tasks(
                on_error, ip=ip, responsible=responsible, status=celery_states.SUCCESS))
            ProcessTask.objects.bulk_create(on_error_tasks)
            root_step.on_error.add(*on_error_tasks)

            _create_step(root_step, workflow_spec, ip, responsible)

            # remove steps without any tasks in any of its descendants
            empty_steps = root_step.get_descendants(include_self=True).filter(tasks=None).exists()
            while empty_steps:
                root_step.get_descendants(include_self=True).filter(
                    child_steps__isnull=True,
                    tasks=None,
                ).delete()
                empty_steps = root_step.get_descendants(
                    include_self=True
                ).filter(tasks=None, child_steps__isnull=True).exists()

            return root_step
