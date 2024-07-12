from .. import db
from bson import ObjectId
from flask_mongoengine import BaseQuerySet
import datetime

class EmployeeBreakHistory(db.DynamicDocument):
   _id = db.ObjectIdField(default=ObjectId, primary_key=True)
   company_id = db.ReferenceField('User')
   employee_details_id = db.ReferenceField('EmployeeDetails')
   start_at =  db.DateTimeField(default=datetime.datetime.now)
   end_at =  db.DateTimeField()
   break_difference = db.DecimalField(precision=0) # Difference by minutes
   attendance_date = db.DateTimeField()
   already_ended = db.BooleanField(default=False)

   meta = { 'collection': 'employee_break_history', 'queryset_class': BaseQuerySet}
   