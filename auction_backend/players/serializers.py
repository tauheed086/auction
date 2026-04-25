from django.db.models import Sum
from rest_framework import serializers
from .models import Auction, Player, Team


class PlayerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = [
            "id",
            "name",
            "mobile_number",
            "role",
            "image",
            "image_url",
            "is_sold",
            "is_skipped",
            "sold_team",
            "sold_points",
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return None

        request = self.context.get("request")
        if request is None:
            return obj.image.url
        return request.build_absolute_uri(obj.image.url)


class AuctionSerializer(serializers.ModelSerializer):
    current_player = PlayerSerializer(read_only=True)
    current_player_id = serializers.PrimaryKeyRelatedField(
        source="current_player",
        queryset=Player.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Auction
        fields = [
            "id",
            "is_active",
            "current_player",
            "current_player_id",
            "team_purse_limit",
            "is_purse_locked",
        ]


class TeamSerializer(serializers.ModelSerializer):
    spent_points = serializers.SerializerMethodField()
    balance_points = serializers.SerializerMethodField()
    players_bought = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "purse_limit",
            "spent_points",
            "balance_points",
            "players_bought",
        ]

    def get_spent_points(self, obj):
        spent = (
            Player.objects.filter(is_sold=True, sold_team=obj.name).aggregate(
                total=Sum("sold_points")
            )["total"]
            or 0
        )
        return int(spent)

    def get_balance_points(self, obj):
        return max(0, int(obj.purse_limit) - self.get_spent_points(obj))

    def get_players_bought(self, obj):
        names = (
            Player.objects.filter(is_sold=True, sold_team=obj.name)
            .exclude(name="")
            .values_list("name", flat=True)
        )
        return list(names)
