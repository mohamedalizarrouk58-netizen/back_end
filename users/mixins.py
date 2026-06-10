"""Shared queryset filters for list endpoints (used with pagination + search)."""


class ListQueryParamFilterMixin:
    """Apply common query-string filters before pagination."""

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        statut = params.get('statut')
        if statut and statut not in ('all', 'tous', ''):
            if statut in ('payee', 'non_payee'):
                if hasattr(self.queryset.model, 'est_payee'):
                    qs = qs.filter(est_payee=statut == 'payee')
            elif hasattr(self.queryset.model, 'statut'):
                qs = qs.filter(statut=statut)

        priorite = params.get('priorite')
        if priorite and priorite not in ('all', 'tous', '') and hasattr(self.queryset.model, 'priorite'):
            qs = qs.filter(priorite=priorite)

        role = params.get('role')
        if role and role != 'all' and hasattr(self.queryset.model, 'role'):
            qs = qs.filter(role=role)

        est_actif = params.get('est_actif')
        if est_actif in ('true', 'false') and hasattr(self.queryset.model, 'est_actif'):
            qs = qs.filter(est_actif=est_actif == 'true')

        return qs
