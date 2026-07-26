from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status
from rest_framework import status


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'pagination'
    max_page_size = 100

    def get_paginated_response(self, data, message=None):
        return Response({
            'total_data': self.page.paginator.count,
            'pagination':self.request.GET.get("pagination", self.page_size),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'message': message,
            'results': data,
        }, status=status.HTTP_200_OK)

    def get_failed_paginated_response(self, message, stat):
        return Response({
            'total_data': None,
            'pagination': self.request.GET.get("pagination", self.page_size),
            'next': None,
            'previous': None,
            'message': message,
            'results': None,
        }, status=stat)

