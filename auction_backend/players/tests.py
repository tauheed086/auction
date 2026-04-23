from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from .models import Auction, Player


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
        auction = Auction.objects.create(is_active=True)
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

    def test_sell_player_marks_current_player_sold(self):
        player = self.create_player("Bumrah")
        auction = Auction.objects.create(is_active=True, current_player=player)
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
        auction = Auction.objects.create(is_active=True, current_player=player)
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
        player.sold_team = "CSK"
        player.sold_points = 700
        player.save(update_fields=["is_sold", "sold_team", "sold_points"])
        auction = Auction.objects.create(is_active=True, current_player=player)
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
