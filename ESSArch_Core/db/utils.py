from django.db.models import Case, CharField, F, IntegerField, Value, When
from django.db.models.functions import Cast, Length, StrIndex, Substr, Trim


def natural_sort(qs, field):
    return qs.annotate(
        ns_len=Length(field),
        ns_split_index=StrIndex(field, Value(' ')),
        ns_suffix=Trim(Substr(field, F('ns_split_index'), output_field=CharField())),
    ).annotate(
        ns_code=Trim(Substr(field, Value(1), 'ns_split_index', output_field=CharField())),
        ns_weight=Case(
            When(ns_split_index=0, then=Value(0)),
            default=Case(
                When(
                    ns_suffix__regex=r'^\d+$',
                    then=Cast(
                        Substr(field, F('ns_split_index'), output_field=CharField()),
                        output_field=IntegerField(),
                    )
                ),
                default=Value(1230),
                output_field=IntegerField()
            ),
            output_field=IntegerField(),
        )
    ).order_by('ns_code', 'ns_weight', 'ns_len', field)
