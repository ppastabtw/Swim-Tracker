from rest_framework import serializers

from apps.swimmers.models import (
    Swimmer, SwimmerSource, Team, SwimmerTeamMembership,
    Meet, Event, SwimTime, RecruitingProfile,
)
from apps.scraping.models import ScrapeJob, ScrapeJobLog


# --- Swimmers ---

class SwimmerListSerializer(serializers.ModelSerializer):
    current_team_name = serializers.SerializerMethodField()

    class Meta:
        model = Swimmer
        fields = ['id', 'full_name', 'gender', 'nationality', 'current_team_name']

    def get_current_team_name(self, obj):
        membership = obj.memberships.filter(is_current=True).select_related('team').first()
        return membership.team.name if membership else None


class SwimmerSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwimmerSource
        fields = ['source', 'external_id', 'profile_url', 'last_scraped_at']


class RecruitingProfileSerializer(serializers.ModelSerializer):
    committed_to_team_name = serializers.CharField(source='committed_to_team.name', default=None)

    class Meta:
        model = RecruitingProfile
        fields = [
            'graduation_year', 'high_school', 'home_state',
            'verbal_commit_date', 'signed_date', 'committed_to_team_name',
            'power_index', 'last_updated',
        ]


class SwimmerDetailSerializer(serializers.ModelSerializer):
    sources = SwimmerSourceSerializer(many=True, read_only=True)
    recruiting_profile = RecruitingProfileSerializer(read_only=True)
    current_team = serializers.SerializerMethodField()

    class Meta:
        model = Swimmer
        fields = [
            'id', 'full_name', 'birth_year', 'gender', 'nationality',
            'created_at', 'updated_at', 'sources', 'recruiting_profile', 'current_team',
        ]

    def get_current_team(self, obj):
        membership = obj.memberships.filter(is_current=True).select_related('team').first()
        if membership:
            return TeamSerializer(membership.team).data
        return None


# --- Teams ---

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'short_name', 'team_type', 'country', 'state']


# --- Meets ---

class MeetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meet
        fields = [
            'id', 'name', 'start_date', 'end_date', 'course',
            'meet_type', 'location_city', 'location_state', 'location_country',
        ]


# --- Events ---

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'distance', 'stroke', 'relay', 'gender']


# --- Swim Times ---

class SwimTimeSerializer(serializers.ModelSerializer):
    event = EventSerializer(read_only=True)
    meet = MeetSerializer(read_only=True)
    swimmer_name = serializers.CharField(source='swimmer.full_name', read_only=True)

    class Meta:
        model = SwimTime
        fields = [
            'id', 'swimmer_name', 'event', 'meet',
            'time_display', 'time_seconds', 'splits',
            'place', 'heat', 'lane', 'dq', 'source', 'scraped_at',
        ]


class ProgressionSerializer(serializers.Serializer):
    """Chart-ready time series for a single event."""
    event = EventSerializer()
    course = serializers.CharField()
    data_points = serializers.ListField(child=serializers.DictField())


# --- Scraping ---

class ScrapeJobLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapeJobLog
        fields = ['level', 'message', 'timestamp']


class ScrapeJobSerializer(serializers.ModelSerializer):
    logs = ScrapeJobLogSerializer(many=True, read_only=True)

    class Meta:
        model = ScrapeJob
        fields = [
            'id', 'job_type', 'source', 'status', 'parameters',
            'result_summary', 'error_detail', 'celery_task_id',
            'triggered_by', 'created_at', 'started_at', 'completed_at', 'logs',
        ]


class ScrapeJobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapeJob
        fields = [
            'id', 'job_type', 'source', 'status',
            'triggered_by', 'created_at', 'completed_at',
        ]


class ScrapeSwimmerRequestSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=['swimcloud', 'swimrankings'])
    external_id = serializers.CharField()


class ScrapeTeamRequestSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=['swimcloud'])
    team_id = serializers.CharField()
    gender = serializers.ChoiceField(choices=['M', 'F'], default='M')
