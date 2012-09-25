


/*function Event(data) {
    this.choices = ko.observable(data.objects.);
    this.time_made = ko.observable();
    this.library = ko.observable();
}

function EventListViewModel() {
    // Data
    var self = this;
    self.events = ko.observableArray([]);
    
    // Operations
    self.addEvent = function() {
        self.events.push(new Event({ title: this.newTaskText() }));
        self.newTaskText("");
    };
    self.removeTask = function(task) { self.tasks.remove(task) };
}

ko.applyBindings(new TaskListViewModel());
*/

  $(document).ready(function() {
  var data = $.getJSON(SCRIPT_ROOT + '/api/event', function(json) {
        alert("JSON Data: " + json.objects[4].choices[3].choice);
        });
  /*var all_data = JSON.parse(data);
  
  var viewModel = ko.mapping.fromJS(all_data);        */

    $("#create-button").click(function() {
        var library = $("#lib_id").val();
        var choices = $('#new_question').serializeArray();

        var new_data = {'choices' : choices.values, 'time' : choices.time_asked}

      $("#makeit").html(JSON.stringify(choices));

         /* $.ajax({
        type: 'POST',
        url: SCRIPT_ROOT + '/api/event',
        dataType: 'json',
        contentType:"binary/octet-stream",
        data: JSON.stringify(new_data),
        error: function(xhr, textStatus, error){
          alert("Didn't work." + error);
            console.log(xhr.statusText);
            console.log(textStatus);
            console.log(error);
        },
        success: function(data) {
          alert("Created" + data.id);
        }
      });*/
  });
});
