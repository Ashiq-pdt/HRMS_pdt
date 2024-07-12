// //________ FullCalendar
// document.addEventListener('DOMContentLoaded', function() {
	
// 	var calendarEl = document.getElementById('calendar');
// 	var calendar = new FullCalendar.Calendar(calendarEl, {
// 		headerToolbar: {
// 			left: 'prev,next today',
// 			center: 'title',
// 			right: 'dayGridMonth,timeGridWeek,timeGridDay'
// 		  },
// 	   navLinks: true, // can click day/week names to navigate views
// 	  businessHours: true, // display business hours
// 	  editable: true,
// 	  selectable: true,
// 	  selectMirror: true,
// 	  droppable: true, // this allows things to be dropped onto the calendar
// 	  drop: function(arg) {
// 		// is the "remove after drop" checkbox checked?
// 		if (document.getElementById('drop-remove').checked) {
// 		  // if so, remove the element from the "Draggable Events" list
// 		  arg.draggedEl.parentNode.removeChild(arg.draggedEl);
// 		}
// 	  },
// 	  select: function(arg) {
// 		var title = prompt('Event Title:');
// 		if (title) {
// 		  calendar.addEvent({
// 			title: title,
// 			start: arg.start,
// 			end: arg.end,
// 			allDay: arg.allDay
// 		  })
// 		}
// 		calendar.unselect()
// 	  },
// 	  eventClick: function(arg) {
// 		if (confirm('Are you sure you want to delete this event?')) {
// 		  arg.event.remove()
// 		}
// 	  },
// 	  editable: true,
// 		eventSources: [sptCalendarEvents, sptBirthdayEvents, sptHolidayEvents, sptOtherEvents],
		
// 	});
// 	calendar.render();
// });	


document.addEventListener('DOMContentLoaded', function() {
	var calendarEl = document.getElementById('calendar');
  
	var calendar = new FullCalendar.Calendar(calendarEl, {
	  headerToolbar: {
		left: 'today prev,next',
		center: 'title',
		right: 'resourceTimelineWeek,resourceTimelineMonth'
	  },
	  views:{
        resourceTimelineWeek: {
          slotDuration: { days: 1 },
		  slotLabelFormat: [
			{ month: 'long', year: 'numeric' }, // top level of text
			{ weekday: 'short',day: 'numeric',month: 'short' } // lower level of text
		  ]
        },
		resourceTimelineMonth: {
			slotLabelFormat: [
			  { month: 'long', year: 'numeric' }, // top level of text
			  { weekday: 'short',day: 'numeric' ,month: 'short'}// lower level of text
			]
		  }
    },
	  selectable: true,
	//   weekends:false,
	  selectOverlap:false, 
	  aspectRatio: 1.6,
	  initialView: 'resourceTimelineWeek',
	  resourceGroupField: 'department', 
	  resources: {{list}},
	  
	  select: function(info) {
		$('#schedule-add').find('input[name=start_date]').val(info.startStr);
		$('#schedule-add').find('input[name=end_date]').val(info.endStr);
		$('#schedule-add').find('input[name=resource_id]').val(info.resource.id);
		$('#schedule-add #shift_employee').text(info.resource.title);
		$('#schedule-add').modal('show');
		$('#submitScheduleBtn').on('click', function(e){
			// We don't want this to act as a link so cancel the link action
			e.preventDefault();
			doSubmit();
		  });
		  function doSubmit(){
			$("#schedule-add").modal('hide');
			calendar.addEvent({
				title: $('#office').val(),
				start: new Date($('#start_date').val() + 'T00:00:00'),
				end: new Date($('#end_date').val() + 'T00:00:00'),
				allDay: true,
				resourceId: $('#resource_id').val(),
				overlap: false,
				display: 'background',
				color: '#ff9f89'
			},true);
			calendar.fullCalendar('unselect');
		   }
	  },
	});
	calendar.render();
  });