from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SwimmerViewSet, MeetViewSet, TeamViewSet, RankingsViewSet, ScrapeViewSet

router = DefaultRouter()
router.register(r'swimmers', SwimmerViewSet)
router.register(r'meets', MeetViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'rankings', RankingsViewSet, basename='rankings')
router.register(r'scrape/jobs', ScrapeViewSet, basename='scrape-jobs')

urlpatterns = [
    path('scrape/swimmer/', ScrapeViewSet.as_view({'post': 'scrape_swimmer'}), name='scrape-swimmer'),
    path('scrape/team/', ScrapeViewSet.as_view({'post': 'scrape_team'}), name='scrape-team'),
    path('', include(router.urls)),
]
