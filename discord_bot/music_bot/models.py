from django.db import models

class SongLog(models.Model):
    url = models.URLField(primary_key=True)
    title = models.CharField(max_length=1000)
    duration = models.FloatField()
    thumbnail = models.ImageField()

    def __str__(self):
        return self.title