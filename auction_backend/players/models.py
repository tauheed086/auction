from django.db import models

# Create your models here.
# players/models.py
class Player(models.Model):
    ROLE_CHOICES = [
        ('batsman', 'Batsman'),
        ('bowler', 'Bowler'),
        ('allrounder', 'All-Rounder'),
    ]

    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    image = models.ImageField(upload_to='players/')
    is_sold = models.BooleanField(default=False)
    is_skipped = models.BooleanField(default=False)
    sold_team = models.CharField(max_length=100, blank=True, default="")
    sold_points = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name
      
class Auction(models.Model):
    current_player = models.ForeignKey(
        Player, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return "Auction Controller"      
