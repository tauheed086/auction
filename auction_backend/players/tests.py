from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from .models import Auction, Player, Team


def get_test_image_file(name="player.gif"):
    image_bytes = (
        b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
        b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
        b"\x00\x00\x02\x02D\x01\x00;"
    )
    return SimpleUploadedFile(name, image_bytes, content_type="image/gif")


class AuctionApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_user(
            username="auctionadmin",
            password="adminpass123",
            is_staff=True,
        )
        self.admin_token = Token.objects.create(user=self.admin_user)
        self.team = Team.objects.create(name="Mumbai Indians", purse_limit=1000)

    def authenticate_as_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")

    def create_player(self, name="Virat"):
        return Player.objects.create(
            name=name,
            role="batsman",
            image=get_test_image_file(f"{name}.gif"),
        )

    def test_current_auction_creates_singleton_when_missing(self):
        self.assertEqual(Auction.objects.count(), 0)

        response = self.client.get("/current-auction/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Auction.objects.count(), 1)
        self.assertIsNone(response.data["current_player"])
        self.assertIn("id", response.data)

    def test_set_player_updates_current_player(self):
        auction = Auction.objects.create(is_active=True, team_purse_limit=1000)
        player = self.create_player("Rohit")
        self.authenticate_as_admin()

        response = self.client.post(
            f"/api/auction/{auction.id}/set_player/",
            {"player_id": player.id},
            format="json",
        )

        auction.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(auction.current_player_id, player.id)
        self.assertEqual(response.data["current_player"]["id"], player.id)

    def test_set_player_allows_preview_before_purse_is_set(self):
        auction = Auction.objects.create(is_active=True, team_purse_limit=None)
        player = self.create_player("Preview Player")
        self.authenticate_as_admin()

        response = self.client.post(
            f"/api/auction/{auction.id}/set_player/",
            {"player_id": player.id},
            format="json",
        )

        auction.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(auction.current_player_id, player.id)

    def test_sell_player_marks_current_player_sold(self):
        player = self.create_player("Bumrah")
        auction = Auction.objects.create(
            is_active=True, current_player=player, team_purse_limit=1000
        )
        self.authenticate_as_admin()

        response = self.client.post(
            f"/api/auction/{auction.id}/sell_player/",
            {"sold_team": "Mumbai Indians", "sold_points": 900},
            format="json",
        )

        player.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(player.is_sold)
        self.assertEqual(player.sold_team, "Mumbai Indians")
        self.assertEqual(player.sold_points, 900)

    def test_sell_player_requires_team_and_points(self):
        player = self.create_player("Shami")
        auction = Auction.objects.create(
            is_active=True, current_player=player, team_purse_limit=1000
        )
        self.authenticate_as_admin()

        response = self.client.post(
            f"/api/auction/{auction.id}/sell_player/",
            {"sold_team": "", "sold_points": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_skip_player_marks_current_player_skipped(self):
        player = self.create_player("Hardik")
        player.is_sold = True
        player.sold_team = "Mumbai Indians"
        player.sold_points = 700
        player.save(update_fields=["is_sold", "sold_team", "sold_points"])
        auction = Auction.objects.create(
            is_active=True, current_player=player, team_purse_limit=1000
        )
        self.authenticate_as_admin()

        response = self.client.post(f"/api/auction/{auction.id}/skip_player/")

        player.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(player.is_sold)
        self.assertTrue(player.is_skipped)
        self.assertEqual(player.sold_team, "")
        self.assertIsNone(player.sold_points)

    def test_create_player_accepts_multipart_upload(self):
        self.authenticate_as_admin()
        payload = {
            "name": "Gill",
            "role": "batsman",
            "image": get_test_image_file("gill.gif"),
        }

        response = self.client.post("/api/players/", payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Player.objects.count(), 1)
        self.assertTrue(Player.objects.first().image.name)

    def test_admin_login_returns_token_for_staff_user(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "auctionadmin", "password": "adminpass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_sell_player_respects_team_purse_limit(self):
        player = self.create_player("Gill")
        auction = Auction.objects.create(
            is_active=True, current_player=player, team_purse_limit=1000
        )
        self.authenticate_as_admin()

        response = self.client.post(
            f"/api/auction/{auction.id}/sell_player/",
            {"sold_team": "Mumbai Indians", "sold_points": 1200},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient purse", response.data["detail"])

    def test_set_initial_purse_applies_to_all_teams_once_before_start(self):
        Team.objects.create(name="CSK", purse_limit=0)
        self.authenticate_as_admin()

        response = self.client.post(
            "/api/teams/set_initial_purse/",
            {"purse_limit": 1200},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(Team.objects.values_list("purse_limit", flat=True)),
            {1200},
        )

        player = self.create_player("Kohli")
        player.is_skipped = True
        player.save(update_fields=["is_skipped"])

        second_response = self.client.post(
            "/api/teams/set_initial_purse/",
            {"purse_limit": 1400},
            format="json",
        )
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot be changed", second_response.data["detail"])

    def test_team_expenses_include_players_spent_and_balance(self):
        self.create_player("Rohit")
        Player.objects.create(
            name="Sky",
            role="batsman",
            image=get_test_image_file("sky.gif"),
            is_sold=True,
            sold_team="Mumbai Indians",
            sold_points=300,
        )
        Player.objects.create(
            name="Bumrah",
            role="bowler",
            image=get_test_image_file("bumrah.gif"),
            is_sold=True,
            sold_team="Mumbai Indians",
            sold_points=250,
        )

        response = self.client.get("/api/teams/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Mumbai Indians")
        self.assertEqual(response.data[0]["spent_points"], 550)
        self.assertEqual(response.data[0]["balance_points"], 450)
        self.assertEqual(response.data[0]["players_bought"], ["Sky", "Bumrah"])
