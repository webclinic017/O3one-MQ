var samples = 20;
var speed = 250;
let timeout = samples * speed;
var values = [];
var labels = [];
var charts = [];
var value = 0;
var count = 0;
var scale = 1;
var ticks = 0;

addEmptyValues(values, samples);

function ws_init() {
    try{
        var ws = new WebSocket("ws://127.0.0.1:8765/");
        count = 0;
        ws.onmessage = function (event) {
            count += 1;
        }
    } catch (error) {
        console.log(error);
        setTimeout(function() {
            ws_init();
        }, speed);
    }
}

ws_init();

function initialize() {
  charts.push(new Chart(document.getElementById("chart0"), {
    type: 'line',
    animation: false,
    data: {
      //labels: labels,
      datasets: [{
        data: values,
        backgroundColor: 'rgba(44, 153, 152, 0.1)',
        borderColor: 'rgb(44, 153, 152)',
        borderWidth: 2,
        lineTension: 0.25,
        pointRadius: 0
      }]
    },
    options: {
      responsive: false,
      animation: false,
      legend: false,
      scales: {
        xAxes: [{
          type: "time",
          display: false
        }],
        yAxes: [{
          ticks: {
            beginAtZero: true
          }
        }]
      }
    }
  })
  );
}

function addEmptyValues(arr, n) {
  for(var i = 0; i < n; i++) {
    arr.push({
      x: moment().subtract((n - i) * speed, 'milliseconds').toDate(),
      y: null
    });
  }
}

function rescale() {
  var padding = [];

  addEmptyValues(padding, 10);
  values.splice.apply(values, padding);

  scale++;
}

function updateCharts(){
  charts.forEach(function(chart) {
    chart.update();
  });
}

function progress() {
  //value = Math.min(Math.max(value + (0.1 - Math.random() / 5), -1), 1);
  value = count;
  values.push({
    x: new Date(),
    y: value
  });
  values.shift();
}

function update_binds() {
    $.ajax({
        url:"/api",
        success:function( data ) {
            if (typeof data.health_text !== undefined) {
                $("#health_text").text(data.health_text);
            }
            if (typeof data.replication_text !== undefined) {
                $("#replication_text").text(data.replication_text);
            }
            if (typeof data.records_text !== undefined) {
                $("#records_text").text(data.records_text);
            }
            if (typeof data.uptime_text !== undefined) {
                $("#uptime_text").text(data.uptime_text);
            }
        }}
    );
}

function advance() {
  if (values[0] !== null && scale < 4) {
    rescale();
    updateCharts();
  }

  updateCharts();
  ticks += 1;

  setTimeout(function() {
    //console.log(count);
    progress();
    if (ticks%10 == 0) {
        update_binds();
    }
    requestAnimationFrame(advance);
    count = 0;
  }, speed);
}

window.onload = function() {
  initialize();
  advance();
};
