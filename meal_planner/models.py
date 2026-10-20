from django.db import models

# Create your models here.

# model for tags
class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    description = models.TextField()

    def __str__(self):
        return self.name

# Model for Main Dish
class MainDish(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    ingredients = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, related_name='main_dishes')

    def __str__(self):
        return self.name
    
# Model for Side Dish
class SideDish(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    ingredients = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, related_name='side_dishes')

    def __str__(self):
        return self.name
    
# Model for Meal
class Meal(models.Model):
    id = models.AutoField(primary_key=True)
    date = models.DateField()
    type = models.CharField(max_length=10, choices=[('Breakfast', 'Breakfast'), ('Lunch', 'Lunch'), ('Snack', 'Snack'), ('Dinner', 'Dinner')])
    main_dish = models.ForeignKey(MainDish, on_delete=models.CASCADE, related_name='meals')
    side_dishes = models.ManyToManyField(SideDish, related_name='meals')
    tags = models.ManyToManyField(Tag, related_name='meals')
    is_plan = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.type} on {self.date}"