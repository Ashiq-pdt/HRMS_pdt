$(function(e){
	'use strict';

	// Timepiocker
	$('#tpBasic').timepicker();

	// Countdonwtimer
	$("#clocktimer").countdowntimer({
		currentTime : true,
		size : "md",
		borderColor : "transparent",
		backgroundColor : "transparent",
		fontColor : "#313e6a",
		// timeZone : "+1"
	});

 });