import django_filters

from apps.swimmers.models import Swimmer, SwimTime, Meet


class SwimmerFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='full_name', lookup_expr='icontains')
    gender = django_filters.CharFilter()
    nationality = django_filters.CharFilter()
    team = django_filters.CharFilter(
        field_name='memberships__team__name', lookup_expr='icontains',
    )

    class Meta:
        model = Swimmer
        fields = ['name', 'gender', 'nationality', 'team']


class SwimTimeFilter(django_filters.FilterSet):
    event = django_filters.NumberFilter(field_name='event__id')
    stroke = django_filters.CharFilter(field_name='event__stroke')
    distance = django_filters.NumberFilter(field_name='event__distance')
    course = django_filters.CharFilter(field_name='meet__course')
    date_after = django_filters.DateFilter(field_name='meet__start_date', lookup_expr='gte')
    date_before = django_filters.DateFilter(field_name='meet__start_date', lookup_expr='lte')

    class Meta:
        model = SwimTime
        fields = ['event', 'stroke', 'distance', 'course', 'date_after', 'date_before']


class MeetFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    course = django_filters.CharFilter()
    meet_type = django_filters.CharFilter()
    date_after = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    date_before = django_filters.DateFilter(field_name='start_date', lookup_expr='lte')

    class Meta:
        model = Meet
        fields = ['name', 'course', 'meet_type', 'date_after', 'date_before']


class RankingsFilter(django_filters.FilterSet):
    stroke = django_filters.CharFilter(field_name='event__stroke')
    distance = django_filters.NumberFilter(field_name='event__distance')
    gender = django_filters.CharFilter(field_name='event__gender')
    course = django_filters.CharFilter(field_name='meet__course')
    date_after = django_filters.DateFilter(field_name='meet__start_date', lookup_expr='gte')

    class Meta:
        model = SwimTime
        fields = ['stroke', 'distance', 'gender', 'course', 'date_after']
