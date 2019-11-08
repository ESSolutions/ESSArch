from functools import update_wrapper

import click


def initialize(f):
    @click.pass_context
    def inner(ctx, *args, **kwargs):
        from ESSArch_Core.config import initialize
        initialize()
        return ctx.invoke(f, *args, **kwargs)

    return update_wrapper(inner, f)
