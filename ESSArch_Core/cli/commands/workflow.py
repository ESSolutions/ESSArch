from datetime import datetime, timedelta

import click
import pytz
from django.conf import settings

from ESSArch_Core.config.decorators import initialize


@initialize
def import_globally():
    global ProcessStep
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
        time_created_end_val = datetime.now() - timedelta(days=int(days_before))
        if hasattr(settings, 'TIME_ZONE'):
            tz = pytz.timezone(settings.TIME_ZONE)
            if time_created_end_val is not None and time_created_end_val.tzinfo is None:
                time_created_end_val = time_created_end_val.replace(tzinfo=pytz.UTC).astimezone(tz)
        time_created_end = time_created_end_val

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
