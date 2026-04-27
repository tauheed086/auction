from django.contrib.auth import authenticate
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
import secrets
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from .models import Player, Auction, Team
from .serializers import AuctionSerializer, PlayerSerializer, TeamSerializer
from rest_framework.response import Response
from rest_framework.views import APIView


def get_or_create_auction():
    auction = Auction.objects.first()
    if auction is None:
        auction = Auction.objects.create(is_active=True)
    sync_purse_lock_state(auction)
    return auction


def has_auction_started(auction):
    return (
        Player.objects.filter(is_sold=True).exists()
        or Player.objects.filter(is_skipped=True).exists()
    )


def sync_purse_lock_state(auction):
    started = has_auction_started(auction)
    if auction.is_purse_locked != started:
        auction.is_purse_locked = started
        auction.save(update_fields=["is_purse_locked"])
    return started


class CurrentAuctionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        auction = get_or_create_auction()
        serializer = AuctionSerializer(auction, context={"request": request})
        return Response(serializer.data)


class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Not allowed."}, status=405)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Not allowed."}, status=405)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Not allowed."}, status=405)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Not allowed."}, status=405)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def sync(self, request):
        names = request.data.get("teams", [])
        if not isinstance(names, list):
            return Response({"detail": "teams must be a list of names."}, status=400)

        auction = get_or_create_auction()
        cleaned = []
        for value in names:
            name = str(value).strip()
            if name:
                cleaned.append(name)

        for name in cleaned:
            defaults = {}
            if auction.team_purse_limit is not None:
                defaults["purse_limit"] = auction.team_purse_limit
            Team.objects.get_or_create(name=name, defaults=defaults)

        serializer = TeamSerializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def set_initial_purse(self, request):
        raw_limit = request.data.get("purse_limit")
        try:
            purse_limit = int(raw_limit)
        except (TypeError, ValueError):
            return Response({"detail": "purse_limit must be a number."}, status=400)

        if purse_limit <= 0:
            return Response(
                {"detail": "purse_limit must be greater than 0."},
                status=400,
            )

        auction = get_or_create_auction()
        has_started = sync_purse_lock_state(auction)
        if has_started:
            return Response(
                {"detail": "Auction already started. Purse cannot be changed now."},
                status=400,
            )

        Team.objects.all().update(purse_limit=purse_limit)
        auction.team_purse_limit = purse_limit
        auction.save(update_fields=["team_purse_limit"])

        serializer = TeamSerializer(self.get_queryset(), many=True)
        return Response(
            {
                "detail": "Initial purse set for all teams.",
                "team_purse_limit": purse_limit,
                "teams": serializer.data,
            }
        )


class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def reset(self, request):
        if not request.user.is_staff:
            return Response(
                {"detail": "Staff access required for auction reset."},
                status=status.HTTP_403_FORBIDDEN,
            )

        pin = str(request.data.get("pin", "")).strip()
        expected_pin = str(getattr(settings, "AUCTION_RESET_PIN", "")).strip()

        if not expected_pin:
            return Response(
                {"detail": "Reset PIN is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not pin:
            return Response({"detail": "pin is required."}, status=400)

        if not secrets.compare_digest(pin, expected_pin):
            return Response({"detail": "Invalid reset PIN."}, status=403)

        with transaction.atomic():
            auction = get_or_create_auction()
            auction.current_player = None
            auction.team_purse_limit = None
            auction.is_purse_locked = False
            auction.save(
                update_fields=["current_player", "team_purse_limit", "is_purse_locked"]
            )

            teams_reset = Team.objects.update(purse_limit=0)
            players_reset = Player.objects.update(
                is_sold=False,
                is_skipped=False,
                sold_team="",
                sold_points=None,
            )

        serializer = AuctionSerializer(auction, context={"request": request})
        return Response(
            {
                "detail": "Auction has been reset successfully.",
                "auction": serializer.data,
                "teams_reset": teams_reset,
                "players_reset": players_reset,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def set_player(self, request, pk=None):
        auction = self.get_object()
        player_id = request.data.get("player_id")
        if not player_id:
            return Response({"detail": "player_id is required."}, status=400)

        player = get_object_or_404(Player, id=player_id)
        auction.current_player = player
        auction.save(update_fields=["current_player"])

        serializer = AuctionSerializer(auction, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def sell_player(self, request, pk=None):
        auction = self.get_object()
        if not auction.current_player:
            return Response({"detail": "No current player selected."}, status=400)

        sold_team = str(request.data.get("sold_team", "")).strip()
        sold_points_raw = request.data.get("sold_points")

        if not sold_team:
            return Response({"detail": "sold_team is required."}, status=400)

        try:
            sold_points = int(sold_points_raw)
        except (TypeError, ValueError):
            return Response({"detail": "sold_points must be a number."}, status=400)

        if sold_points <= 0:
            return Response({"detail": "sold_points must be greater than 0."}, status=400)

        if auction.team_purse_limit is None:
            return Response(
                {"detail": "Set team purse limit before selling players."},
                status=400,
            )

        team = Team.objects.filter(name__iexact=sold_team).first()
        if not team:
            return Response(
                {"detail": f"Team '{sold_team}' does not exist. Set team purse first."},
                status=400,
            )

        current_player = auction.current_player
        already_committed = (
            Player.objects.filter(is_sold=True, sold_team=team.name)
            .exclude(id=current_player.id)
            .aggregate(total=Sum("sold_points"))["total"]
            or 0
        )
        remaining = int(team.purse_limit) - int(already_committed)
        if sold_points > remaining:
            return Response(
                {
                    "detail": (
                        f"Insufficient purse for {team.name}. "
                        f"Remaining: {remaining}, attempted: {sold_points}."
                    )
                },
                status=400,
            )

        auction.current_player.is_sold = True
        auction.current_player.is_skipped = False
        auction.current_player.sold_team = team.name
        auction.current_player.sold_points = sold_points
        auction.current_player.save(
            update_fields=["is_sold", "is_skipped", "sold_team", "sold_points"]
        )
        if not auction.is_purse_locked:
            auction.is_purse_locked = True
            auction.save(update_fields=["is_purse_locked"])

        serializer = AuctionSerializer(auction, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def skip_player(self, request, pk=None):
        auction = self.get_object()
        if auction.team_purse_limit is None:
            return Response(
                {"detail": "Set team purse limit before processing players."},
                status=400,
            )

        if auction.current_player:
            auction.current_player.is_sold = False
            auction.current_player.is_skipped = True
            auction.current_player.sold_team = ""
            auction.current_player.sold_points = None
            auction.current_player.save(
                update_fields=["is_sold", "is_skipped", "sold_team", "sold_points"]
            )
            if not auction.is_purse_locked:
                auction.is_purse_locked = True
                auction.save(update_fields=["is_purse_locked"])

        serializer = AuctionSerializer(auction, context={"request": request})
        return Response(serializer.data)


class AdminLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        password = request.data.get("password", "")
        user = authenticate(request=request, username=username, password=password)

        if not user:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_staff:
            return Response(
                {"detail": "Staff access required for admin dashboard."},
                status=status.HTTP_403_FORBIDDEN,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "username": user.username, "is_staff": user.is_staff}
        )


class AdminMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "username": request.user.username,
                "is_staff": request.user.is_staff,
            }
        )


class AdminLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.auth:
            request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
