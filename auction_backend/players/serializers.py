from rest_framework import serializers
from .models import Auction, Player


class PlayerSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = [
            "id",
            "name",
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
        fields = ["id", "is_active", "current_player", "current_player_id"]
