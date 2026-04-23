from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from .models import Player, Auction
from .serializers import AuctionSerializer, PlayerSerializer
from rest_framework.response import Response
from rest_framework.views import APIView


def get_or_create_auction():
    auction = Auction.objects.first()
    if auction is None:
        auction = Auction.objects.create(is_active=True)
    return auction


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


class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

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

        auction.current_player.is_sold = True
        auction.current_player.is_skipped = False
        auction.current_player.sold_team = sold_team
        auction.current_player.sold_points = sold_points
        auction.current_player.save(
            update_fields=["is_sold", "is_skipped", "sold_team", "sold_points"]
        )

        serializer = AuctionSerializer(auction, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def skip_player(self, request, pk=None):
        auction = self.get_object()

        if auction.current_player:
            auction.current_player.is_sold = False
            auction.current_player.is_skipped = True
            auction.current_player.sold_team = ""
            auction.current_player.sold_points = None
            auction.current_player.save(
                update_fields=["is_sold", "is_skipped", "sold_team", "sold_points"]
            )

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
