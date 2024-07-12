document.addEventListener('DOMContentLoaded', function() {
	var calendarEl = document.getElementById('calendar');
  
	var calendar = new FullCalendar.Calendar(calendarEl, {
	resourceAreaWidth:"15%",
	height: "auto",
	expandRows:true,
	weekends:true,
	// hiddenDays: {{company_details.week_off | default(0)}},
	  headerToolbar: {
		left: 'prev,next',
		center: 'title',
		right: 'resourceTimelineWeek,resourceTimelineMonth'
	  },
	  views:{
        resourceTimelineWeek: {
          slotDuration: { days: 1 },
		//   slotMinWidth : 30,
		  slotLabelFormat: [
			{ month: 'long', year: 'numeric' }, // top level of text
			{ weekday: 'short',day: 'numeric',month: 'short' } // lower level of text
		  ],
		  
        },
		resourceTimelineMonth: {
			slotLabelFormat: [
			  { month: 'long', year: 'numeric' }, // top level of text
			  { weekday: 'short',day: 'numeric' ,month: 'short'}// lower level of text
			]
		  },
    },
	customButtons: {
		printButton: {
		  icon: 'print',
		  click: function() {
			window.print();
		  }
		},
		prev: {
			text: 'Prev',
			click: function () {
			  // do the original command
			  calendar.prev();
			  $('#start_date').val(moment(calendar.currentData.dateProfile.activeRange.start).format('YYYY-MM-DD'))
			  $('#end_date').val(moment(calendar.currentData.dateProfile.activeRange.end).subtract(1, "days").format('YYYY-MM-DD'))
			} },
		  next: {
			text: 'Next',
			click: function () {
			  // do the original command
			  calendar.next();
			  // do something after
			  $('#start_date').val(moment(calendar.currentData.dateProfile.activeRange.start).format('YYYY-MM-DD'))
			  $('#end_date').val(moment(calendar.currentData.dateProfile.activeRange.end).subtract(1, "days").format('YYYY-MM-DD'))
			} }
	},
	editable: false,
	selectable: false,
	selectOverlap:false, 
	// aspectRatio: 2.6,
	// filterResourcesWithEvents:true,
	initialView: 'resourceTimelineWeek',
	resourceGroupField: 'department', 
	resources: {{list}},
	resourceAreaHeaderContent: 'List of Employees', 
	resourceOrder: '-department',
	resourceGroupLabelContent: function(arg) {
		if(arg.groupValue){
			return { html: '<input type="checkbox" class="checkbox" name="resource_group_checkbox" id="'+arg.groupValue.replace(/\s/g, '')+'" value="'+arg.groupValue.replace(/\s/g, '')+'" />' + " " + arg.groupValue };
		}
		else{
			return { html: arg.groupValue + ' <span style="color:red">No Department Selected</span>' };
		}
	},
	resourceLabelContent: function(arg) {
		return { html: '<input id="'+arg.resource.id+'" type="checkbox" class="checkbox resource_checkbox '+arg.resource.extendedProps.department.replace(/\s/g, '')+'" data-parent="'+arg.resource.extendedProps.department.replace(/\s/g, '')+'" name="resource_checkbox" value="'+arg.resource.id+'"/>' + " " + arg.resource.title };
	},
	events: {{eventList}},
	//Remove Single Event
	// eventClick: function(arg) {
    //     if (confirm('Are you sure you want to delete this event?')) {
    //       arg.event.remove()
    //     }
	// }
	});

	// On load populate the current calender week date
	$('#start_date').val(moment(calendar.currentData.dateProfile.activeRange.start).format('YYYY-MM-DD'))
	$('#end_date').val(moment(calendar.currentData.dateProfile.activeRange.end).subtract(1, "days").format('YYYY-MM-DD'))

	// Action on schedule button
	$('.scheduleBtn').on('click', function(e) {
        e.preventDefault();
		swal({
			title: "Are you sure?",
			text: "You want to create schedule for selected employee(s)? If you have assigned same shifts for a day it won't reflect! ",
			icon: "info",
			buttons: true,
			dangerMode: true,
		}).then((willDelete) => {
			if (willDelete) {
				var res_arr = []
				$('input.resource_checkbox[type=checkbox]').each(function () {
					if ($(this).is(":checked")) {
						var resource_id = (this.checked ? $(this).val() : "")
						res_arr.push(resource_id)
					}
				});
				createEvent(res_arr);
			} 
		});
		
    });
	function createEvent(res_arr){
		$("#schedule-add").modal('hide');
		$("#global-loader").show();
		cs = "{{ csrf_token() }}";
		// Ajax Start
		$.ajax({
			headers: {
				'X-CSRFTOKEN': cs
			},
			url: '/masschedule/shifts/',
			data: {work_timing:$('#work_timing :selected').val(),employee_ids:res_arr,schedule_from:$('#start_date').val(),schedule_till:$('#end_date').val(),allow_outside_checkin:$('#allow_outside_checkin :selected').val(),company_id:$('#company_id').val(),work_office:$('#working_office :selected').val()},
			type: 'POST',
		})
		.done(function (data) {
			$("#global-loader").fadeOut("slow");
			if(data.status == "success"){
				$.each(data.eventList, function( key, value ) {
					calendar.addEvent({
										id: value.id,
										title: value.title,
										start: value.start,
										end: value.end,
										allDay: true,
										resourceId: value.resourceId,
										overlap: false,
										display: 'auto',
										color: value.color
									},true);
				  });
				swal({
					title: "Success",
					text: "Successfully Created Schedule(s)!",
					icon: "success",
				}); 
			}
			else{
				//  $('#message').html(data.message);
				 swal({
					title: "Error",
					text: "Same shift already scheduled for the day!",
					icon: "error",
				}); 
			}
		})
		.fail(function (err) {
			$('#message').html(err);
		})
		// Ajax End
	}

	// Action on Clear schedule button
	$('.clearSchedule').on('click', function(e) {
        e.preventDefault();
		swal({
			title: "Are you sure?",
			text: "Once Cleared, you will not be able to recover these schedules!",
			icon: "warning",
			buttons: true,
			dangerMode: true,
		}).then((willDelete) => {
			if (willDelete) {
			var res_arr = []
			$('input.resource_checkbox[type=checkbox]').each(function () {
				if ($(this).is(":checked")) {
					var resource_id = (this.checked ? $(this).val() : "")
					res_arr.push(resource_id)
				}
			});
			deleteEvent(res_arr);
			} 
		});
		
    });

	function deleteEvent(res_arr){
		$("#schedule-add").modal('hide');
		$("#global-loader").show();
		cs = "{{ csrf_token() }}";
		// Ajax Start
		$.ajax({
			headers: {
				'X-CSRFTOKEN': cs
			},
			url: '/deletemasschedule/shifts/',
			data: {employee_ids:res_arr,schedule_from:$('#start_date').val(),schedule_till:$('#end_date').val()},
			type: 'POST',
		})
		.done(function (data) {
			$("#global-loader").fadeOut("slow");
			if(data.status == "success"){
				$.each(data.eventList, function( key, value ) {
					ev = calendar.getEventById(value.id)
					ev.remove()
				});
				swal({
					title: "Success",
					text: "Successfully Deleted Schedule(s)!",
					icon: "success",
				}); 
			}
			else{
					$('#message').html(data.message);
					swal({
					title: "Error",
					text: "No shifts scheduled for these date range!",
					icon: "error",
				}); 
			}
		})
		.fail(function (err) {
			$('#message').html(err);
		})
	}
	calendar.render();
  });