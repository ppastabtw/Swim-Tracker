from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Min

from apps.swimmers.models import Swimmer, Team, Meet, SwimTime, Event
from apps.scraping.models import ScrapeJob
from apps.scraping.tasks import scrape_swimmer_by_id, scrape_team_roster

from .serializers import (
    SwimmerListSerializer, SwimmerDetailSerializer,
    TeamSerializer, MeetSerializer, SwimTimeSerializer,
    EventSerializer, ProgressionSerializer,
    ScrapeJobSerializer, ScrapeJobListSerializer,
    ScrapeSwimmerRequestSerializer, ScrapeTeamRequestSerializer,
)
from .filters import SwimmerFilter, SwimTimeFilter, MeetFilter, RankingsFilter


class SwimmerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Swimmer.objects.all()
    filterset_class = SwimmerFilter
    search_fields = ['full_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return SwimmerListSerializer
        return SwimmerDetailSerializer

    @action(detail=True)
    def times(self, request, pk=None):
        swimmer = self.get_object()
        times = SwimTime.objects.filter(swimmer=swimmer).select_related('event', 'meet')
        filterset = SwimTimeFilter(request.query_params, queryset=times)
        serializer = SwimTimeSerializer(filterset.qs, many=True)
        return Response(serializer.data)

    @action(detail=True, url_path='best_times')
    def best_times(self, request, pk=None):
        swimmer = self.get_object()
        # Best time per event + course combination
        times = SwimTime.objects.filter(
            swimmer=swimmer, dq=False,
        ).select_related('event', 'meet')

        best = {}
        for t in times:
            key = (t.event_id, t.meet.course)
            if key not in best or t.time_seconds < best[key].time_seconds:
                best[key] = t

        serializer = SwimTimeSerializer(best.values(), many=True)
        return Response(serializer.data)

    @action(detail=True, url_path='progression/(?P<event_id>[^/.]+)')
    def progression(self, request, pk=None, event_id=None):
        swimmer = self.get_object()
        event = Event.objects.get(id=event_id)
        times = SwimTime.objects.filter(
            swimmer=swimmer, event=event, dq=False,
        ).select_related('meet').order_by('meet__start_date')

        data_points = []
        for t in times:
            data_points.append({
                'date': t.meet.start_date.isoformat(),
                'time_seconds': str(t.time_seconds),
                'time_display': t.time_display,
                'meet_name': t.meet.name,
                'course': t.meet.course,
            })

        return Response({
            'event': EventSerializer(event).data,
            'data_points': data_points,
        })

    @action(detail=True)
    def meets(self, request, pk=None):
        swimmer = self.get_object()
        meet_ids = SwimTime.objects.filter(swimmer=swimmer).values_list('meet_id', flat=True).distinct()
        meets = Meet.objects.filter(id__in=meet_ids).order_by('-start_date')
        serializer = MeetSerializer(meets, many=True)
        return Response(serializer.data)


class MeetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Meet.objects.all()
    serializer_class = MeetSerializer
    filterset_class = MeetFilter
    search_fields = ['name']

    @action(detail=True)
    def results(self, request, pk=None):
        meet = self.get_object()
        times = SwimTime.objects.filter(meet=meet).select_related('swimmer', 'event')
        filterset = SwimTimeFilter(request.query_params, queryset=times)
        serializer = SwimTimeSerializer(filterset.qs, many=True)
        return Response(serializer.data)

    @action(detail=True)
    def events(self, request, pk=None):
        meet = self.get_object()
        event_ids = SwimTime.objects.filter(meet=meet).values_list('event_id', flat=True).distinct()
        events = Event.objects.filter(id__in=event_ids)
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    search_fields = ['name', 'short_name']

    @action(detail=True)
    def roster(self, request, pk=None):
        team = self.get_object()
        memberships = team.memberships.filter(is_current=True).select_related('swimmer')
        swimmers = [m.swimmer for m in memberships]
        serializer = SwimmerListSerializer(swimmers, many=True)
        return Response(serializer.data)

    @action(detail=True)
    def recruiting(self, request, pk=None):
        team = self.get_object()
        from .serializers import RecruitingProfileSerializer
        profiles = team.recruitingprofile_set.all() if hasattr(team, 'recruitingprofile_set') else []
        # Get recruiting profiles for swimmers on this team
        from apps.swimmers.models import RecruitingProfile
        swimmer_ids = team.memberships.values_list('swimmer_id', flat=True)
        profiles = RecruitingProfile.objects.filter(swimmer_id__in=swimmer_ids)
        serializer = RecruitingProfileSerializer(profiles, many=True)
        return Response(serializer.data)


class RankingsViewSet(viewsets.GenericViewSet):
    """Top times — requires stroke, distance, and gender params."""
    serializer_class = SwimTimeSerializer
    filterset_class = RankingsFilter

    def get_queryset(self):
        return SwimTime.objects.filter(dq=False).select_related('swimmer', 'event', 'meet')

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())

        # Must have at least stroke + distance + gender
        params = request.query_params
        if not all(params.get(k) for k in ('stroke', 'distance', 'gender')):
            return Response(
                {'detail': 'stroke, distance, and gender are required parameters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = int(params.get('limit', 100))
        qs = qs.order_by('time_seconds')[:limit]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class ScrapeViewSet(viewsets.GenericViewSet):
    """Scrape trigger and job tracking endpoints."""
    queryset = ScrapeJob.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return ScrapeJobListSerializer
        return ScrapeJobSerializer

    def list(self, request):
        jobs = self.get_queryset().order_by('-created_at')[:50]
        serializer = ScrapeJobListSerializer(jobs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        job = self.get_object()
        serializer = ScrapeJobSerializer(job)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='swimmer')
    def scrape_swimmer(self, request):
        ser = ScrapeSwimmerRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        job = ScrapeJob.objects.create(
            job_type='swimmer_times',
            source=ser.validated_data['source'],
            status='pending',
            parameters={'external_id': ser.validated_data['external_id']},
            triggered_by='api',
        )

        scrape_swimmer_by_id.delay(
            ser.validated_data['source'],
            ser.validated_data['external_id'],
            str(job.id),
        )

        return Response(ScrapeJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'], url_path='team')
    def scrape_team(self, request):
        ser = ScrapeTeamRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        job = ScrapeJob.objects.create(
            job_type='team_roster',
            source=ser.validated_data['source'],
            status='pending',
            parameters={
                'team_id': ser.validated_data['team_id'],
                'gender': ser.validated_data['gender'],
            },
            triggered_by='api',
        )

        scrape_team_roster.delay(
            ser.validated_data['source'],
            ser.validated_data['team_id'],
            ser.validated_data['gender'],
            str(job.id),
        )

        return Response(ScrapeJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        job = self.get_object()
        if job.status != 'failed':
            return Response(
                {'detail': 'Can only retry failed jobs.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_job = ScrapeJob.objects.create(
            job_type=job.job_type,
            source=job.source,
            status='pending',
            parameters=job.parameters,
            triggered_by='api',
        )

        if job.job_type == 'swimmer_times':
            scrape_swimmer_by_id.delay(
                job.source,
                job.parameters.get('external_id', ''),
                str(new_job.id),
            )
        elif job.job_type == 'team_roster':
            scrape_team_roster.delay(
                job.source,
                job.parameters.get('team_id', ''),
                job.parameters.get('gender', 'M'),
                str(new_job.id),
            )

        return Response(ScrapeJobSerializer(new_job).data, status=status.HTTP_202_ACCEPTED)
