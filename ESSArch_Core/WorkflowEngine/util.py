import importlib
import logging

from celery import states as celery_states
from django.core.cache import cache
from django.db import transaction
from tenacity import (
    RetryError,
    Retrying,
    stop_after_delay,
    wait_random_exponential,
)

from ESSArch_Core.WorkflowEngine.models import ProcessStep, ProcessTask


def get_result(step, reference):
    tasks = ProcessTask.objects.values_list('reference', 'result').filter(processstep=step, reference__isnull=False)
    results = dict((x, y) for x, y in tasks)

    if isinstance(reference, list):
        return [results[ref] for ref in reference]

    return results[reference]


def _create_on_error_tasks(parent, errors, ip=None, responsible=None, eager=False, status=celery_states.PENDING):
    for on_error_idx, on_error in enumerate(errors):
        args = on_error.get('args', [])
        params = on_error.get('params', {})
        result_params = on_error.get('result_params', {})
        progress = 0
        if status == celery_states.SUCCESS:
            progress = 100
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
            processstep=parent,
            processstep_pos=on_error_idx,
            status=status,
            progress=progress,
        )


def _create_step(parent, flow, ip, responsible, context=None):
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
                parent=parent,
                parent_pos=e_idx,
                eager=parent.eager,
                information_package=ip,
                context=context,
                responsible=responsible,
            )

            on_error_tasks = list(_create_on_error_tasks(
                child_s, flow_entry.get('on_error', []), ip=ip, responsible=responsible,
                eager=parent.eager
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
                queue=flow_entry.get('queue', None),
                reference=flow_entry.get('reference', None),
                label=flow_entry.get('label'),
                args=args,
                params=params,
                result_params=result_params,
                eager=parent.eager,
                allow_failure=flow_entry.get('allow_failure', False),
                information_package=ip,
                responsible=responsible,
                processstep=parent,
                processstep_pos=e_idx,
                hidden=flow_entry.get('hidden', False),
                run_if=flow_entry.get('run_if', ''),
                log=flow_entry.get('log'),
            )

            on_error_tasks = list(
                _create_on_error_tasks(parent, flow_entry.get('on_error', []), ip=ip, responsible=responsible)
            )
            ProcessTask.objects.bulk_create(on_error_tasks)
            task.on_error.add(*on_error_tasks)


def _add_steps(parent, steps):
    for e_idx, step in enumerate(steps):
        step.parent = parent
        step.parent_pos = e_idx
        step.save(update_fields=['parent', 'parent_pos'])


def create_workflow(workflow_spec=None, ip=None, workflow_steps=None, name='', label='', on_error=None, eager=False,
                    context=None, responsible=None, part_root=None, run_state='', top_root_step=None):
    if workflow_spec is None:
        workflow_spec = []
    if workflow_steps is None:
        workflow_steps = []
    if on_error is None:
        on_error = []
    if context is None:
        context = {}
    if responsible is None:
        responsible = getattr(ip, 'responsible', None)

    logger = logging.getLogger('essarch.workflow')

    with cache.lock('create_workflow_lock', timeout=300):
        try:
            for attempt in Retrying(stop=stop_after_delay(30),
                                    wait=wait_random_exponential(multiplier=1, max=60)):
                with attempt:
                    try:
                        with transaction.atomic():
                            with ProcessStep.objects.delay_mptt_updates():
                                if top_root_step:
                                    root_step = ProcessStep(
                                        name=name, eager=eager, information_package=ip, context=context,
                                        responsible=responsible, label=label, part_root=part_root,
                                        run_state=run_state)
                                    root_step.parent = top_root_step
                                    root_step.parent_pos = top_root_step.child_steps.count() + 1
                                    root_step.save()
                                else:
                                    root_step = ProcessStep.objects.create(
                                        name=name, eager=eager, information_package=ip, context=context,
                                        responsible=responsible, label=label, part_root=part_root,
                                        run_state=run_state)
                                on_error_tasks = list(_create_on_error_tasks(
                                    root_step, on_error, ip=ip, responsible=responsible, status=celery_states.SUCCESS))
                                ProcessTask.objects.bulk_create(on_error_tasks)
                                root_step.on_error.add(*on_error_tasks)

                                if workflow_spec:
                                    _create_step(root_step, workflow_spec, ip, responsible)

                                if workflow_steps:
                                    _add_steps(root_step, workflow_steps)

                            root_step.refresh_from_db()
                            with ProcessStep.objects.delay_mptt_updates():
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
                    except RuntimeError as e:
                        logger.warning('Exception in create_workflow for ip: {}, error: {} - retry'.format(ip, e))
                        raise
        except RetryError:
            logger.warning('RetryError in create_workflow for ip: {}'.format(ip))
            raise
    return root_step
