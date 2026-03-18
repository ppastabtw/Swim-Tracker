from django.contrib import admin
from .models import Swimmer, SwimmerSource, Team, SwimmerTeamMembership, Meet, Event, SwimTime, RecruitingProfile

admin.site.register(Swimmer)
admin.site.register(SwimmerSource)
admin.site.register(Team)
admin.site.register(SwimmerTeamMembership)
admin.site.register(Meet)
admin.site.register(Event)
admin.site.register(SwimTime)
admin.site.register(RecruitingProfile)
