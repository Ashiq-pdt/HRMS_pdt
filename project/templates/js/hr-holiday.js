$(function (e) {
	'use strict';

	// Datepicker
	$('.fc-datepicker').datepicker({
		dateFormat: "dd MM yy",
		zIndex: 1,
	});


	// Datepicker
	$('[data-bs-toggle="modaldatepicker"]').datepicker({
		autoHide: true,
		zIndex: 999998,
	});

	// Data Table
	// $('#hr-holiday').DataTable({
	// 	"order": [
	// 		[0, "desc"]
	// 	],
	// 	order: [],
		
	// 	language: {
	// 		searchPlaceholder: 'Search...',
	// 		sSearch: '',

	// 	}
	// });


	// Select2
	$('.select2').select2({
		minimumResultsForSearch: Infinity,
		width: '100%'
	});

});

/*---- Full Calendar -----*/
document.addEventListener('DOMContentLoaded', function () {
	var calendarEl = document.getElementById('calendar1');
	var calendar = new FullCalendar.Calendar(calendarEl, {
		headerToolbar: {
			left: 'prev next',
			center: 'title',
			right: 'dayGridMonth listDay,listWeek,listMonth,listYear'
		},
		views: {
			dayGridMonth: { buttonText: 'Month View' },
			listDay: { buttonText: 'Day List' },
			listWeek: { buttonText: 'Week List' },
			listMonth: { buttonText: 'Month List' },
			listYear: { buttonText: 'Year List' }
		},
		selectable:true,
		select: function (info) {
			// console.log(info)
			$('#holidaymodal').modal('toggle');
			$('input[name=occasion_date]').val(moment(info.start).format('DD-MM-YYYY'));
			calendar.unselect()
		},
		eventClick: function (arg) {
			swal({
				title: "Are you sure?",
				text: "You want to delete this event/holiday? ",
				icon: "warning",
				buttons: true,
				dangerMode: true,
			}).then((willDelete) => {
				if (willDelete) {
					cs = $('#csrf_gen').val()
					var event_id = arg.event._def.publicId
					$.ajax({
							headers: {
								'X-CSRF-TOKEN': cs
							},
							url: '/delete/holiday/',
							data: {id:event_id},
							type: 'POST',
						}).done(function (data) {
							var holiday_data = '';
							if (data.status == "success") {
								arg.event.remove()
								swal({
									title: "Success",
									text: "Successfully Created Event/Holiday!",
									icon: "success",
								});
							}
						})
						.fail(function (err) {
							console.log(err);
							$('#message').html(err);
						})
				}
			});
		},
		dayMaxEvents: true, // allow "more" link when too many events
		events: {{list}}
	});
	// Action on Holiday button
    $('.addHolidayBtn').click(function (e) {
        e.preventDefault();
        swal({
            title: "Are you sure?",
            text: "You want to save this day as event/holiday? ",
            icon: "info",
            buttons: true,
            dangerMode: true,
        }).then((willDelete) => {
            if (willDelete) {
                cs = $('#csrf_gen').val()
                $.ajax({
                        headers: {
                            'X-CSRF-TOKEN': cs
                        },
                        url: '/create/holiday/',
                        data: $('#add_holiday_form').serialize(),
                        type: 'POST',
                    }).done(function (data) {
                        $('#holidaymodal').modal('toggle');
                        var holiday_data = '';
                        if (data.status == "success") {
							calendar.addEvent(data.event)
                            swal({
                                title: "Success",
                                text: "Successfully Created Event/Holiday!",
                                icon: "success",
                            });
                        }
                    })
                    .fail(function (err) {
                        console.log(err);
                        $('#message').html(err);
                    })
            }
        });
    });
	calendar.render();
});