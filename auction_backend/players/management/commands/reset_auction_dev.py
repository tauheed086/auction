from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from players.models import Auction, Player, Team


class Command(BaseCommand):
    help = (
        "Dev utility: reset auction lock/purse so initial purse can be set again. "
        "Optionally clear sold/skipped player results."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help=(
                "Also reset sold/skipped/player sale data "
                "(is_sold, is_skipped, sold_team, sold_points)."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow running even when DEBUG is False.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "This command is blocked when DEBUG=False. Use --force if intended."
            )

        auction = Auction.objects.first()
        if auction is None:
            auction = Auction.objects.create(is_active=True)

        auction.current_player = None
        auction.team_purse_limit = None
        auction.is_purse_locked = False
        auction.save(
            update_fields=["current_player", "team_purse_limit", "is_purse_locked"]
        )

        teams_updated = Team.objects.update(purse_limit=0)
        players_updated = 0
        if options["full"]:
            players_updated = Player.objects.update(
                is_sold=False,
                is_skipped=False,
                sold_team="",
                sold_points=None,
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Auction dev reset complete. "
                f"auction_id={auction.id}, teams_reset={teams_updated}, "
                f"players_reset={players_updated}"
            )
        )
