from .models import ActivityLog
def create_activity_log(request,requestor,company_id):
    activity_log = ActivityLog()
    activity_log.company_id = company_id
    activity_log.log_user = requestor
    activity_log.remote_addr = request.remote_addr
    activity_log.method = request.method
    activity_log.scheme = request.scheme
    activity_log.full_path = request.full_path
    activity_log.request_form = request.form
    activity_log.save()
    
    return activity_log    