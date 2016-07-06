var $results = $('#results')
var template = $('template').html()


function set_size(){
  $results.height($(document).height() - 90)
}

$(document).ready(set_size)
$(window).resize(set_size)

var socket = new WebSocket('ws://localhost:8000');

socket.onmessage = function (event) {
  var data = JSON.parse(event.data)
  console.log(data)
  $results.html(Mustache.render(template, data))
}
