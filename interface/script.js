var editRow = null;
var tempData = null;

function cancelEdit(){
	if (editRow != null && tempData != null){
		editRow.html(tempData);
		editRow = null;
		tempData = null;
	}
	$("tr#task_new").remove();
}

function saveTask(){
	if (editRow == null) return;
	var task_id = editRow.attr("id").substring(5);
	var name = $.trim( $("#newName").removeClass("required").val() );
	var cmd = $.trim( $("#newCmd").removeClass("required").val() );
	var shell = $("#newShell").is(":checked");
	if (name == "" || cmd == ""){
		if (name == "") $("#newName").addClass("required");
		if (cmd == "") $("#newCmd").addClass("required");
		return;
	}

	$.post(
		"/save/"+task_id,
		{"name":name,"cmd":cmd,"shell":shell},
		function(data){
			window.location = "/";
		},
		"text"
	);
}

$(document).on("click", "div#addTask", function(){
	if (editRow != null){
		if (confirm("Cancel your current edits?") == false) return;
	}
	cancelEdit();
	var html = "<tr id='task_new'>\
	<td><input id='newName' type='text'/></td>\
	<td><input id='newCmd' type='text'/></td>\
	<td><input id='newShell' type='checkbox'/></td>\
	<td></td><td></td>\
	<td><a id='cancelEdit'>Cancel</a></td>\
	<td><a id='saveTask'>Save</a></td>\
	</tr>";
	$("table#tasks").append(html);
	editRow = $("#task_new");
});

$(document).on("click", "a.editTask", function(event){
	if (editRow != null){
		if (confirm("Cancel your current edits?") == false) return;
	}
	cancelEdit();
	editRow = $(this).parent().parent();
	tempData = editRow.html();
	var html = "";
	html += "<td><input id='newName' type='text' value='"+editRow.children("td:nth-child(1)").text()+"'/></td>";
	html += "<td><input id='newCmd' type='text' value='"+editRow.children("td:nth-child(2)").text()+"'/></td>";
	var shell = (editRow.find("input[type='checkbox']").attr("checked") != undefined) ? "checked" : "";
	html += "<td><input id='newShell' type='checkbox' "+shell+"/></td>";
	html += "<td></td><td></td>\
	<td><a id='cancelEdit'>Cancel</a></td>\
	<td><a id='saveTask'>Save</a></td>";
	editRow.html(html);
});

$(document).on("click", "a#cancelEdit", function(){cancelEdit()});
$(document).on("click", "a#saveTask", function(){saveTask()});