from datetime import datetime 
from mongoengine import DynamicDocument, ReferenceField, DateField, MapField, ListField

class SIF(DynamicDocument):
    company = ReferenceField('CompanyDetails')
    start_date = DateField()
    end_date = DateField()
    sub_company = ReferenceField('SubCompanies', default=None)
    created_on = DateField(default=datetime.now)
    created_by = ReferenceField('User')
    EDR_records = MapField(field=ListField(ReferenceField('EDR')), default={})
    SCRs = MapField(field=ReferenceField('SCR'), default={})
    
    meta = {
        'collection': 'sif',
    }
