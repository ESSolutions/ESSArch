import click


def deactivate_prompts(ctx, param, value):
    if value:
        for p in ctx.command.params:
            if isinstance(p, click.Option) and p.prompt is not None:
                p.prompt = None
    return value
