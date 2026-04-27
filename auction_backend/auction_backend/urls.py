from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from players.views import (
    AuctionViewSet,
    PlayerViewSet,
    TeamViewSet,
    CurrentAuctionView,
    AdminLoginView,
    AdminMeView,
    AdminLogoutView,
)

router = DefaultRouter()
router.register(r'players', PlayerViewSet)
router.register(r'teams', TeamViewSet)
router.register(r'auction', AuctionViewSet)
urlpatterns = [
    path('api/', include(router.urls)),
    path('api/auth/login/', AdminLoginView.as_view()),
    path('api/auth/me/', AdminMeView.as_view()),
    path('api/auth/logout/', AdminLogoutView.as_view()),
    path('admin/', admin.site.urls),
    path('current-auction/', CurrentAuctionView.as_view())
]

if settings.DEBUG or getattr(settings, "SERVE_MEDIA_FILES", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
