    function index1(){
        "use strict";
        /*----- Employees ------*/
        var options = {
            series: [{{company_details.employees|selectattr('gender', 'equalto', 'male')|list|length }}, {{company_details.employees|selectattr('gender', 'equalto', 'female')|list|length }}],
            chart: {
                height:300,
                type: 'donut',
            },
            dataLabels: {
                enabled: false
            },
    
            legend: {
                show: false,
            },
             stroke: {
                show: true,
                width:0
            },
            plotOptions: {
            pie: {
                donut: {
                    size: '80%',
                    background: 'transparent',
                    labels: {
                        show: true,
                        name: {
                            show: true,
                            fontSize: '29px',
                            color:'#6c6f9a',
                            offsetY: -10
                        },
                        value: {
                            show: true,
                            fontSize: '26px',
                            color: undefined,
                            offsetY: 16,
                            formatter: function (val) {
                                return val
                            }
                        },
                        total: {
                            show: true,
                            showAlways: false,
                            label: 'Total',
                            fontSize: '22px',
                            fontWeight: 600,
                            color: '#373d3f',
                          }
    
                    }
                }
            }
            },
            responsive: [{
                options: {
                    legend: {
                        show: false,
                    }
                }
            }],
            labels: ["Male","Female"],
            colors: [myVarVal, '#fe7f00'],
        };
        document.getElementById('employees').innerHTML = ''; 
        var chart = new ApexCharts(document.querySelector("#employees"), options);
        chart.render();
    }

    
function index(){
	// LIne-Chart 
	var ctx = document.getElementById("chartLine").getContext('2d');
	var myChart = new Chart(ctx, {

		data: {
			labels: [{% for item in company_details.departments %}
                        "{{ item.department_name }}",
                    {% endfor %}],
			datasets: [{
				label: 'Total BUdget',
				data: [{% for item in company_details.departments %}
                        {{company_details.employees|selectattr('employee_company_details.department', 'equalto',item.department_name)|list|length}},
                    {% endfor %}],
				borderWidth: 3,
				backgroundColor: 'transparent',
				borderColor: myVarVal,
				pointBackgroundColor: '#ffffff',
				pointRadius: 0,
				type: 'line',
			},
			]
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			layout: {
				padding: {
					left: 0,
					right: 0,
					top: 0,
					bottom: 0
				}
			},
			tooltips: {
				enabled: false,
			},
			scales: {
				yAxes: [{
					gridLines: {
						display: true,
						drawBorder: false,
						zeroLineColor: 'rgba(142, 156, 173,0.1)',
						color: "rgba(142, 156, 173,0.1)",
					},
					scaleLabel: {
						display: false,
					},
					ticks: {
						beginAtZero: true,
						min: 0,
						max: 25,
						stepSize: 1,
						fontColor: "#8492a6",
					},
				}],
				xAxes: [{
					ticks: {
						beginAtZero: true,
						fontColor: "#8492a6",
					},
					gridLines: {
						color: "rgba(142, 156, 173,0.1)",
						display: false
					},

				}]
			},
			legend: {
				display: false
			},
			elements: {
				point: {
					radius: 0
				}
			}
		}
	});
}

function ticketoverview(){
	'use strict';
	// Ticketstatistics
	var ctx = document.getElementById("ticketoverview").getContext('2d');
	var myChart = new Chart(ctx, {
		type: 'bar',
		data: {
			labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
			datasets: [
			{
				label: 'Total # of Expiring Documents',
				categoryPercentage: 0.2,
				barPercentage: 0.8,
				data: [{% for i in range(1,13) %}
					{% set ns = namespace(counter=0) %}
					{% set st = namespace(start=td.replace(day=1,month=i)) %}
					{% set en = namespace(end=td.replace(day=1,month=i)) %}
					{% if i == 12 %}
						{% set en = namespace(end=td.replace(day=1,month=1,year=td.year+1)) %}
					{% else %}
						{% set en = namespace(end=td.replace(day=1,month=i+1)) %} 
					{% endif %}
						{% for employees in company_details.employees%} 
							{% for document in employees.documents|selectattr('document_expiry_on', 'greaterthan',st.start)|selectattr('document_expiry_on', 'lessthan',en.end)|selectattr('document_type', 'ne','offer_letter') %} 
									{% set ns.counter = ns.counter + 1 %}
							{% endfor %}
						{% endfor %}
						{{ns.counter}},
				{% endfor %}],
				borderWidth: 2,
				backgroundColor: '#fe7f00',
				borderColor: '#fe7f00',
				pointBackgroundColor: '#fe7f00',
				pointRadius: 0,
				type: 'bar',
			},
			]
		},
		options: {
			maintainAspectRatio: false,
			responsive: true,
			legend: {
				display: false,
				labels: {
					display: false
				}
			},
			scales: {
				yAxes: [{
					ticks: {
						beginAtZero: true,
						fontSize: 10,
						max: 30,
						fontColor: "#b4b7c5",
					},
					gridLines: {
						color: 'rgba(180, 183, 197, 0.4)'
					}
				}],
				xAxes: [{
					barPercentage: 3,
					ticks: {
						beginAtZero: true,
						fontSize: 11,
						fontColor: "#b4b7c5",
					},
					gridLines: {
						color: 'rgba(180, 183, 197, 0.4)'
					}
				}]
			}
		}
	});

}