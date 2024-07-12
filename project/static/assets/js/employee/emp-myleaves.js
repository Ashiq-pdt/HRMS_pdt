$(function(e){
	'use strict';

	
	/* Data Table */
	$('#emp-attendance').DataTable({
		order: [],
		columnDefs: [ { orderable: false, targets: [0] } ],
		language: {
			searchPlaceholder: 'Search...',
			sSearch: '',

		}
	});
	/* End Data Table */

	//Daterangepicker with Callback
	$('input[name="singledaterange"]').daterangepicker({
		singleDatePicker: true,
        locale: {
            format: 'DD/MM/YYYY'
        }
	}, function(start, label) {
		$('.no_of_days').html('1')
		$('#no_of_days').val('1')
		// console.log("A new date selection was made: " + start.format('MMMM D, YYYY'));
	});
	$('input[name="daterange"]').daterangepicker({
		opens: 'left',
        locale: {
            format: 'DD/MM/YYYY'
        }
	  }, function(start, end, label) {
		const oneDay = 24 * 60 * 60 * 1000; // hours*minutes*seconds*milliseconds
		const diffDays = Math.round(Math.abs((start - end) / oneDay));
		$('.no_of_days').html(diffDays)
		$('#no_of_days').val(diffDays)
	});

	$('#daterange-categories').on('change', function() {
		$('.leave-content').hide();
		$('#' + $(this).val()).show();
	});
 });