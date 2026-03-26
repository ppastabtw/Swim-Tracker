from django.contrib import admin
from .models import Swimmer, SwimmerSource, Team, SwimmerTeamMembership, Meet, Event, SwimTime, RecruitingProfile


class SwimmerSourceInline(admin.TabularInline):
    model = SwimmerSource
    extra = 0


class SwimmerTeamMembershipInline(admin.TabularInline):
    model = SwimmerTeamMembership
    extra = 0


@admin.register(Swimmer)
class SwimmerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'gender', 'nationality', 'birth_year', 'created_at']
    list_filter = ['gender', 'nationality']
    search_fields = ['full_name']
    inlines = [SwimmerSourceInline, SwimmerTeamMembershipInline]


@admin.register(SwimmerSource)
class SwimmerSourceAdmin(admin.ModelAdmin):
    list_display = ['swimmer', 'source', 'external_id', 'last_scraped_at']
    list_filter = ['source']
    search_fields = ['swimmer__full_name', 'external_id']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'team_type', 'state', 'country']
    list_filter = ['team_type', 'country']
    search_fields = ['name', 'short_name']


@admin.register(SwimmerTeamMembership)
class SwimmerTeamMembershipAdmin(admin.ModelAdmin):
    list_display = ['swimmer', 'team', 'season_year', 'is_current']
    list_filter = ['is_current', 'season_year']
    search_fields = ['swimmer__full_name', 'team__name']


@admin.register(Meet)
class MeetAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'course', 'meet_type', 'location_city']
    list_filter = ['course', 'meet_type', 'location_country']
    search_fields = ['name', 'location_city']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'distance', 'stroke', 'relay', 'gender']
    list_filter = ['stroke', 'gender', 'relay']


@admin.register(SwimTime)
class SwimTimeAdmin(admin.ModelAdmin):
    list_display = ['swimmer', 'event', 'time_display', 'meet', 'place', 'dq']
    list_filter = ['event__stroke', 'dq', 'source']
    search_fields = ['swimmer__full_name']
    raw_id_fields = ['swimmer', 'meet', 'event']


@admin.register(RecruitingProfile)
class RecruitingProfileAdmin(admin.ModelAdmin):
    list_display = ['swimmer', 'graduation_year', 'high_school', 'home_state', 'committed_to_team']
    list_filter = ['graduation_year', 'home_state']
    search_fields = ['swimmer__full_name', 'high_school']
    raw_id_fields = ['swimmer', 'committed_to_team']
