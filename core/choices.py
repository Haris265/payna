from django.db import models

class TransactionStatusChoices(models.IntegerChoices):
    PENDING = 0, 'Pending'         
    SUCCESS = 1, 'Success' 
    FAILED = 2, 'Failed' 









