from datetime import timedelta

import click
from django.utils import timezone

from ESSArch_Core.config.decorators import initialize


@initialize
def import_globally():
    global ProcessStep
    global app
    from ESSArch_Core.config.celery import app
    from ESSArch_Core.WorkflowEngine.models import ProcessStep


@click.command()
@click.option("--step_id", type=str, help="The ID of the step to remove.")
@click.option("--name", type=str, help="The name of the step to remove.")
@click.option("--status", type=str, default='SUCCESS', show_default=True,
              help="The status of the step to match for removal. (SUCCESS, STARTED, PENDING, FAILURE)")
@click.option("--run_state", type=str, default='SUCCESS', show_default=True,
              help="The run state of the step to match for removal. (SUCCESS, STARTED, PENDING, FAILURE)")
@click.option("--time_created_start", type=str, help="The start time for filtering steps by creation time.")
@click.option("--time_created_end", type=str, help="The end time for filtering steps by creation time.")
@click.option("--days_before", type=str, help="Remove steps older than this many days.")
@click.option("--preview", is_flag=True,
              help="Preview the steps that would be removed without actually removing them.")
def remove_step(step_id=None, name=None, status='SUCCESS', run_state='SUCCESS', time_created_start=None,
                time_created_end=None, days_before=None, preview=False):
    """Remove process step"""
    import_globally()
    if step_id is None and name is None:
        print("You must specify either a step_id or a name to remove a step.")
        exit(1)

    if days_before is not None:
        time_created_end = timezone.now() - timedelta(days=int(days_before))

    filter = {}
    if step_id is not None:
        filter['id'] = step_id
    if name is not None:
        filter['name'] = name
    if run_state is not None:
        filter['run_state'] = run_state
    if time_created_start is not None:
        filter['time_created__gte'] = time_created_start
    if time_created_end is not None:
        filter['time_created__lte'] = time_created_end
    for step in ProcessStep.objects.filter(**filter):
        # If a specific status is provided, check it
        if step.status == status:
            if preview:
                print(f"Preview: Step {step.label} ({step.id}) would be removed.")
                continue
            step.delete()
            print(f"Step {step.label} ({step.id}) has been removed.")
        else:
            print(f"Step {step.label} ({step.id}) does not match the specified status '{status}'.")


@click.command()
@click.option("--task_id", type=str, help="The ID to revoke.")
@click.option("--all", is_flag=True, help="Revoke all tasks.")
@click.option("--chord_unlock", is_flag=True, help="Revoke chord_unlock tasks.")
@click.option("--ip_id", type=str, help="Revoke chord_unlock tasks for ip_id.")
@click.option("--print_task", is_flag=True, help="Print task info.")
@click.option("--preview", is_flag=True, help="Preview the taks that would be revoked.")
def revoke_task(task_id=None, all=False, chord_unlock=False, ip_id=None, preview=False, print_task=False):
    """Revoke task"""
    import_globally()
    i = app.control.inspect()
    if task_id:
        print(f"Revoke {task_id}.")
        app.control.revoke(task_id, terminate=True)

    if chord_unlock:
        jobs = i.scheduled()
        for hostname in jobs:
            tasks = jobs[hostname]
            print(f'Scheduled tasks {hostname}: {len(tasks)}')
            for task in tasks:
                if task['request']['name'] == 'celery.chord_unlock':
                    if print_task:
                        print('Found chord_unlock task: {}'.format(task))
                    try:
                        task_ip = (task['request']['args'][1]['kwargs']['tasks'][1]['options']
                                   ['headers']['headers']['ip'])
                    except KeyError:
                        task_ip = 'KeyError'
                    if ip_id and ip_id and not task_ip == ip_id:
                        print(f"{task_ip} does not match ip_id: {ip_id}.")
                        continue
                    if preview:
                        print(f"Preview: revoke {task['request']['name']} ({task['request']['id']}).")
                    else:
                        print(f"Revoke {task['request']['name']} ({task['request']['id']}).")
                        app.control.revoke(task['request']['id'], terminate=True)
                elif print_task:
                    print('Print task: {}'.format(task))

    if all:
        # remove pending tasks
        if not preview:
            app.control.purge()

        # remove active tasks
        jobs = i.active()
        for hostname in jobs:
            tasks = jobs[hostname]
            print(f'Active tasks {hostname}: {len(tasks)}')
            for task in tasks:
                if print_task:
                    print('Print task: {}'.format(task))
                if preview:
                    print(f"Preview: revoke {task['name']} ({task['id']}).")
                else:
                    print(f"Revoke {task['name']} ({task['id']}).")
                    app.control.revoke(task['id'], terminate=True)

        # remove reserved tasks
        jobs = i.reserved()
        for hostname in jobs:
            tasks = jobs[hostname]
            print(f'Reserved tasks {hostname}: {len(tasks)}')
            for task in tasks:
                if print_task:
                    print('Print task: {}'.format(task))
                if preview:
                    print(f"Preview: revoke {task['name']} ({task['id']}).")
                else:
                    print(f"Revoke {task['name']} ({task['id']}).")
                    app.control.revoke(task['id'], terminate=True)

        # remove scheduled tasks
        jobs = i.scheduled()
        for hostname in jobs:
            tasks = jobs[hostname]
            print(f'Scheduled tasks {hostname}: {len(tasks)}')
            for task in tasks:
                if print_task:
                    print('Print task: {}'.format(task))
                if preview:
                    print(f"Preview: revoke {task['request']['name']} ({task['request']['id']}).")
                else:
                    print(f"Revoke {task['request']['name']} ({task['request']['id']}).")
                    app.control.revoke(task['request']['id'], terminate=True)
