# players/admin.py

from django.contrib import admin
from .models import Player, Auction

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'is_sold', 'is_skipped']
    list_filter = ['role', 'is_sold']

@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ['current_player', 'is_active']