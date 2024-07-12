(function($) {
	"use strict";
		
		//transfer
		var languages = [
		];

		var groupData = [
				{% for item in company_details.departments %}
					{
						"groupName": "{{item.department_name}}",
						{% set ns = namespace(gd=[]) %}
							{% for item in company_details.employees|selectattr("employee_company_details.department", "equalto", item.department_name)%} 
										{% set ns.gd = ns.gd + [{"Name": item.first_name + ' ' +item.last_name, "value": item.id|string() }] %}
							{% endfor %}
						"groupData": {{ns.gd}}
					},
				{% endfor %}
		];

		var settings = {
			"inputId": "languageInput",
			"data": languages,
			"groupData": groupData,
			"itemName": 'Name',
			"groupItemName": "groupName",
			"groupListName" : "groupData",
			"container": "transfer",
			"valueName": 'value',
			"callable" : function (data, names) {
				console.log("Selected ID：" + data)
				$("#selectedItemSpan").text(names)
			}
		};
		Transfer.transfer(settings);	
})(jQuery);