from django.db import models


class Comment(models.Model):
    """Комментарий. user_id и author берутся из JWT — без FK на User."""
    user_id = models.IntegerField(db_index=True)
    author = models.CharField(max_length=150)
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author}: {self.text[:50]}"

    def to_dict(self):
        return {
            "id": self.pk,
            "user_id": self.user_id,
            "author": self.author,
            "text": self.text,
            "created_at": self.created_at.isoformat(),
        }
