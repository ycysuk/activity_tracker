# activity_tracker
an activity tracker

inspired by [ActivityWatch](https://activitywatch.net/)

[activity_tracker.py](https://github.com/ycysuk/activity_tracker/blob/main/activity_tracker.py)
scans active windows per 100ms

record applications, window titles, timestamps in sqlite db


[at_server](https://github.com/ycysuk/activity_tracker/blob/main/at_server.py)
reads db and visualizes in browser <http://localhost:5601/>

# screenshots

category barchart & donut chart

![Screenshot 1](https://github.com/ycysuk/activity_tracker/blob/main/screenshots/Screenshot%201.png)

title & app barcharts

![Screenshot 2](https://github.com/ycysuk/activity_tracker/blob/main/screenshots/Screenshot%202.png)

category timeline, zoomable in horizontal

![Screenshot 3](https://github.com/ycysuk/activity_tracker/blob/main/screenshots/Screenshot%203.png)

category rule editor

![Screenshot 4](https://github.com/ycysuk/activity_tracker/blob/main/screenshots/Screenshot%204.png)


# References

get active window

<https://stackoverflow.com/questions/10266281/obtain-active-window-using-python>

<https://www.programcreek.com/python/example/81370/win32gui.GetForegroundWindow>

d3.js bar, donut, timeline chart

<https://observablehq.com/@d3/donut-chart>

<https://observablehq.com/@d3/horizontal-bar-chart>

<https://observablehq.com/@tezzutezzu/world-history-timeline>

<https://observablehq.com/@d3/zoomable-bar-chart>

single instance

<https://stackoverflow.com/questions/380870/make-sure-only-a-single-instance-of-a-program-is-running>

notify in win32

<https://pypi.org/project/win10toast/>
