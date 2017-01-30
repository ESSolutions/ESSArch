"""
    ESSArch is an open source archiving and digital preservation system

    ESSArch Tools for Producer (ETP)
    Copyright (C) 2005-2017 ES Solutions AB

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

    Contact information:
    Web - http://www.essolutions.se
    Email - essarch@essolutions.se
"""

from django_datatables_view.base_datatable_view import DatatableMixin
from rest_framework import viewsets, mixins, permissions, views
from rest_framework.response import Response

class DatatableBaseView(views.APIView, DatatableMixin):
    
    absolute_url_link_flag = False
    qs = None

    def get_initial_queryset(self):
        if self.qs:
            return self.qs
        elif self.model:
            return self.model.objects.all()
        else:
            raise NotImplementedError('Need to provide a model or qs "queryset" or implement get_initial_queryset!')
    
    def render_column(self, row, column):
        """ Renders a column on a row
        """

        if hasattr(row, 'get_%s_display' % column):
            # It's a choice field
            text = getattr(row, 'get_%s_display' % column)()
        else:
            try:
                text = getattr(row, column)
            except AttributeError:
                obj = row
                for part in column.split('.'):
                    if obj is None:
                        break
                    obj = getattr(obj, part)

                text = obj
        if text is None:
            text = self.none_string
        
        if hasattr(text,'all'):
            data = []
            for item in text.all():
                d={}
                for column in self.get_columns():
                    d[column]=self.render_column(item, column)
                data.append(d)
            text=data
        
        if text and hasattr(row, 'get_absolute_url') and self.absolute_url_link_flag:
            return '<a href="%s">%s</a>' % (row.get_absolute_url(), text)
        else:
            return text

    is_clean = False

    def prepare_results(self, qs):
        data = []
        for item in qs:
            d={}
            for column in self.get_columns():
                d[column]=self.render_column(item, column)
            data.append(d)
        return data

    def post(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.request = request
        response = None

        try:
            func_val = self.get_context_data(**kwargs)
            if not self.is_clean:
                assert isinstance(func_val, dict)
                response = dict(func_val)
                if 'result' not in response:
                    response['result'] = 'ok'
            else:
                response = func_val
        except KeyboardInterrupt:
            # Allow keyboard interrupts through for debugging.
            raise
        except Exception as e:
            #logger.error('JSON view error: %s' % request.path, exc_info=True)

            # Come what may, we're returning JSON.
            if hasattr(e, 'message'):
                msg = e.message
                msg += str(e)
            else:
                msg = _('Internal error') + ': ' + str(e)
            response = {'result': 'error',
                        'sError': msg,
                        'text': msg}

        return Response(response)