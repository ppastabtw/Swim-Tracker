from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

# TODO: Register viewsets here once implemented
# router.register(r'swimmers', SwimmerViewSet)
# router.register(r'meets', MeetViewSet)
# router.register(r'teams', TeamViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
