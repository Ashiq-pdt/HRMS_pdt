// document.addEventListener('DOMContentLoaded', function() {
// 	var calendarEl = document.getElementById('calendar1');
// 	let selector = document.querySelector("#selector");
// 	var calendar = new FullCalendar.Calendar(calendarEl, {
// 	   headerToolbar: {
// 		left: 'prev',
// 		center: 'title',
// 		right: 'next dayGridMonth'

// 	  },
// 	//   navLinks: true, // can click day/week names to navigate views
// 	//   selectable: false,
// 	  navLinks: true,
// 	  dayMaxEvents: true,
// 	  dayMaxEventRows: 2,// allow "more" link when too many events
// 	  events: {{leave_list}},
// 	  eventDidMount: function(arg) {
// 		let val = selector.value;
// 		console.log(val)
// 		if (!(val == arg.event.extendedProps.userId || val == "all")) {
// 		  arg.el.style.display = "none";
// 		}
// 	  }
// 	});
// 	calendar.render();
// 	document.querySelector("#selector").addEventListener('change', function() {
// 		calendar.refetchEvents();
// 	});
// });	

document.addEventListener('DOMContentLoaded', function() {

	// let currentDayDate = new Date().toISOString().slice(0, 10);
	let selector = document.querySelector("#selector");
	let calendarEl = document.getElementById('calendar1');
  
	let calendar = new FullCalendar.Calendar(calendarEl, {
	  allDaySlot: true,
	  headerToolbar: {
		left: 'prev,next',
		center: 'title',
		right: 'dayGridMonth'
	  },	
	  navLinks: true,
	  dayMaxEvents: true,
	  dayMaxEventRows: 2,// allow "more" link when too many events
	  eventDidMount: function(arg) {
		let val = selector.value;
		if (!(val == arg.event.extendedProps.userId || val == "all")) {
		  arg.el.style.display = "none";
		}
		if (val == "all") {
			arg.el.style.display = "block";
		}
	  },
	  events: function (fetchInfo, successCallback, failureCallback) {
		if("{{session['is_super_approver']}}" === 'True'){
			successCallback({{super_leave_list}});
		}
		else{
			successCallback({{leave_list}});
		}
		
	  }
	});
	calendar.render();
  
	selector.addEventListener('change', function() {
	  calendar.refetchEvents();
	});
  });