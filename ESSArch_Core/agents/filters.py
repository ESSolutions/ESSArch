from django.db.models import F, OuterRef, Subquery, TextField
from django.db.models.functions import Concat
from rest_framework.filters import OrderingFilter

from ESSArch_Core.agents.models import AgentName


class AgentOrderingFilter(OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if ordering:
            if any(v in ['latest_name', '-latest_name'] for v in ordering):
                latest_name = Subquery(
                    AgentName.objects.filter(
                        agent=OuterRef('pk')
                    ).annotate(
                        name=Concat('part', 'main', output_field=TextField())
                    ).order_by(F('start_date').desc(nulls_first=True)).values('name')[:1]
                )
                queryset = queryset.annotate(latest_name=latest_name)

        return super().filter_queryset(request, queryset, view)
