import dash
from firebase import firebase
import datetime
from dash import html, dcc, Input, Output, callback, State
import dash_ag_grid as dag
import base64
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeSwitchAIO
import plotly.graph_objs as go
import pytz
import pandas as pd

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

# Initialize Firebase
firebase = firebase.FirebaseApplication('https://central-hub-7fe3e-default-rtdb.firebaseio.com/', None)

# Define the desired time zone
desired_timezone = pytz.timezone('America/New_York')  # For example, 'America/New_York'


def parse_temperature(temp_str):
    return float(temp_str.replace('C', '').strip())


@app.callback(
    Output('table', 'rowData'),
    [Input('interval-component', 'n_intervals')]
)
def update_table(n):
    data = firebase.get('/lora_data', None)

    table_data = []
    for key, entry in data.items():
        value_components = entry['value'].split(', ')
        timestamp = entry['timestamp']
        timestamp = datetime.datetime.fromtimestamp(timestamp, tz=pytz.timezone('America/New_York'))
        timestamp_with_suffix = timestamp.strftime('%Y-%m-%d %I:%M:%S %p')
        avg_temperature_str = value_components[2].split(':')[1]
        avg_temperature = parse_temperature(avg_temperature_str)
        compass = value_components[1].split(':')[1]
        angle = value_components[3].split(':')[1]
        fire_severity = value_components[4].split(':')[1]

        if timestamp.date() == datetime.datetime.now().date():
            table_data.append({
                'timestamp': timestamp_with_suffix,
                'average temperature (°C)': avg_temperature,
                'compass': compass,
                'angle (°)': angle,
                'fire severity (%)': fire_severity
            })

    return table_data


@callback(
    Output("table", "exportDataAsCsv"),
    Input("csv-button", "n_clicks"),
)
def export_data_as_csv(n_clicks):
    if n_clicks:
        return True
    return False


@app.callback(
    Output('fire-severity-graph', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_fire_severity_graph(n):
    data_graph = firebase.get('/lora_data', None)

    timestamps = []
    avg_temperatures = []
    fire_severities = []

    for key, entry in data_graph.items():
        value_components = entry['value'].split(', ')
        timestamp = datetime.datetime.fromtimestamp(entry['timestamp'], tz=pytz.timezone('America/New_York'))
        if timestamp.date() == datetime.datetime.now().date():
            avg_temperature_str = value_components[2].split(':')[1]
            fire_severity_str = value_components[4].split(':')[1]

            avg_temperature = parse_temperature(avg_temperature_str)
            fire_severity = float(fire_severity_str.replace('%', '').strip())

            timestamps.append(timestamp.strftime('%I:%M:%S %p'))
            avg_temperatures.append(avg_temperature)
            fire_severities.append(fire_severity)

    fig = go.Figure(layout_template='plotly_dark')

    fig.add_trace(go.Scatter(x=timestamps, y=avg_temperatures, name='Average Temperature', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=timestamps, y=fire_severities, name='Fire Severity', mode='lines+markers', yaxis='y2'))

    fig.update_layout(
        title='Fire Severity and Average Temperature Over Time',
        title_font_size=50,
        title_xanchor="auto",
        title_yanchor="middle",
        yaxis_title='Average Temperature (°C)',
        font_size=15,
        yaxis2=dict(
            title='Fire Severity (%)',
            overlaying='y',
            side='right'
        ),
        xaxis_title='Time',
    )

    return fig


@app.callback(
    Output('latest-info', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_info_box(n_intervals):
    data_graph = firebase.get('/lora_data', None)

    if data_graph:
        latest_entry = list(data_graph.values())[-1]
        value_components = latest_entry['value'].split(', ')
        timestamp = datetime.datetime.fromtimestamp(latest_entry['timestamp'], tz=pytz.timezone('America/New_York'))
        avg_temperature_str = value_components[2].split(':')[1]
        fire_severity_str = value_components[4].split(':')[1]

        latest_timestamp = timestamp.strftime('%Y-%m-%d %I:%M:%S %p')
        latest_avg_temp = f"Latest Avg Temp: {avg_temperature_str.strip()}"
        latest_fire_severity = f"Latest Fire Severity: {fire_severity_str.strip()}"

        latest_info = f"{latest_timestamp}, {latest_avg_temp}, {latest_fire_severity}"

        return html.P(latest_info, id="latest-info-content", style={'font-size': '20px', 'text-align': 'center'})
    else:
        return "No data"


def getting_node_info():
    data_node = firebase.get('/lora_data', None)
    node_one = node_two = central_hub = "Unknown"  # Default values in case data is not available
    for key, entry in data_node.items():
        value_components = entry['value'].split(', ')
        for component in value_components:
            if 'Nodeone' in component:
                node_one = component.split(':')[1]
            elif 'Nodetwo' in component:
                node_two = component.split(':')[1]
            elif 'Centralhub' in component:
                central_hub = component.split(':')[1]

    node_status = [
        {'name': 'NODE ONE', 'status': node_one},
        {'name': 'NODE TWO', 'status': node_two},
        {'name': 'CENTRAL HUB', 'status': central_hub},
    ]

    return node_status


def generate_node_status_content():
    return html.Ul([
        html.Li([
            html.Span(f"{node['name']}: ", style={'font-size': '20px'}),
            dbc.Badge("ON", color="success") if node['status'] == ' 1' else dbc.Badge("OFF", color="danger")
        ]) for node in getting_node_info()
    ], style={'list-style-type': 'none', 'text-align': 'center'})


@app.callback(
    Output('node-status-display', 'children'),  # Target the component that displays node status
    Input('update-interval', 'n_intervals')  # Assuming you have an Interval component that triggers updates
)
def update_node_status(n):
    # No need to pass 'n' if it's not used in the function, it's just there to trigger the callback
    return generate_node_status_content()


def parse_severity(sev_str):
    return float(sev_str.replace('%', '').strip())


def fetch_latest_fire_severity():
    data_sev = firebase.get('/lora_data', None)

    for key, entry in data_sev.items():
        value_components = entry['value'].split(', ')
        fire_severity = value_components[4].split(':')[1]

    return parse_severity(fire_severity)


previous_status = None
alert_triggered_for_current_danger_status = False


def determine_badge_properties_based_on_severity():
    global previous_status, alert_triggered_for_current_danger_status
    fire_severity = fetch_latest_fire_severity()  # Assuming this function fetches the latest fire severity

    if fire_severity > 80:
        current_status = "Danger"
    elif fire_severity > 50:
        current_status = "Warning"
    else:
        current_status = "Safe"

    trigger_alert = False
    # Trigger an alert only if we transition to "Danger" from a different status,
    # and ensure we haven't already triggered an alert for this "Danger" status.
    if current_status == "Danger" and (previous_status != "Danger" or not alert_triggered_for_current_danger_status):
        trigger_alert = True
        alert_triggered_for_current_danger_status = True  # Mark that we've triggered an alert for this "Danger" status
    elif current_status != "Danger":
        # Reset the flag if we move out of "Danger", allowing for future alerts if we return to "Danger".
        alert_triggered_for_current_danger_status = False

    previous_status = current_status

    if current_status == "Danger":
        return "Danger", "danger", "High fire severity detected. Immediate action required.", trigger_alert
    elif current_status == "Warning":
        return "Warning", "warning", "Medium fire severity detected. Be cautious.", False
    else:
        return "Safe", "success", "Low fire severity. No immediate danger.", False


@app.callback(
    [Output('notification-button', 'children'),
     Output('popover', 'is_open'),
     Output('popover-body', 'children')],
    [Input('notification-button', 'n_clicks'),
     Input('update-interval', 'n_intervals')],
    [State('popover', 'is_open')]
)
def update_notification_area(n_clicks, n_intervals, is_open):
    badge_text, badge_color, popover_message, trigger_alert = determine_badge_properties_based_on_severity()

    button_children = [
        "Notifications",
        dbc.Badge(badge_text, color=badge_color, text_color="white", className="ms-1")
    ]

    if trigger_alert:
        is_open = True
    elif n_clicks:
        is_open = not is_open

    return button_children, is_open, popover_message


popover = dbc.Popover(
    [
        dbc.PopoverHeader("Notifications Info"),
        dbc.PopoverBody("Default message", id='popover-body'),
    ],
    id="popover",
    target="notification-button",
    trigger="hover",
)

columnDefs = [
    {"field": "timestamp", "name": "Timestamp"},
    {"field": "average temperature (°C)", "name": "Average Temperature"},
    {"field": "compass", "name": "Compass"},
    {"field": "angle (°)", "name": "Angle"},
    {"field": "fire severity (%)", "name": "Fire Severity"},
]


def generate_table():
    return html.Ul([
        dbc.Button(
            children=[
                html.I(className="fas fa-download mr-2"),  # using Font Awesome icons
                "Download Data"
            ],
            id="csv-button",
            n_clicks=0,
            color="info",
            className="btn-block",
            style={
                'position': 'absolute',
                'top': '250px',
                'left': '10px'
            }
        ),
        dag.AgGrid(
            id='table',
            columnDefs=columnDefs,
            columnSize="sizeToFit",
            defaultColDef={"filter": True, "sortable": True},
            dashGridOptions={"pagination": True, "animateRows": True},
            style={"width": "100%", "height": "500px", 'position': 'absolute', 'top': '300px', 'left': '0px'},
            csvExportParams={
                "fileName": "ag_grid_test.csv",
            },
            className="ag-theme-alpine-dark",

        ),
        dcc.Interval(
            id='interval-component',
            interval=5000,  # in milliseconds
            n_intervals=0
        )
    ])


def latest_info():
    return html.Ul([
        dbc.Card(
            id='latest-info',
            children=[
                dbc.CardBody([
                    html.P("No data", id="latest-info-content", style={'font-size': '50px'})
                ])
            ],
            color="dark",
            style={"width": "50%", "height": "50px", "position": "absolute", "top": "250px", "right": "0px"},
            inverse=True
        ),
    ])


@app.callback(
    Output("download-csv", "data"),
    [Input("download-btn", "n_clicks")],
    [State("date-picker-single", "date")]
)
def download_logged_history(n_clicks, selected_date):
    if n_clicks > 0:
        data = firebase.get('/lora_data', None)
        rows = []

        selected_date_dt = datetime.datetime.strptime(selected_date, '%Y-%m-%d')

        for key, entry in data.items():
            value_components = entry['value'].split(', ')
            timestamp = entry['timestamp']
            entry_datetime = datetime.datetime.fromtimestamp(timestamp, tz=pytz.timezone('America/New_York'))

            if entry_datetime.date() == selected_date_dt.date():  # Filter for the selected date
                avg_temperature = parse_temperature(value_components[2].split(':')[1])
                compass = value_components[1].split(':')[1]
                angle = value_components[3].split(':')[1]
                fire_severity = value_components[4].split(':')[1]

                rows.append({
                    'timestamp': entry_datetime.strftime('%Y-%m-%d %I:%M:%S %p'),
                    'average temperature (°C)': avg_temperature,
                    'compass': compass,
                    'angle (°)': angle,
                    'fire severity (%)': fire_severity
                })

        # Convert list of dictionaries to DataFrame and then to CSV
        df = pd.DataFrame(rows)
        return dcc.send_data_frame(df.to_csv, filename=f"logged_history_{selected_date}.csv")


tab1_content = dbc.Card(
    dbc.CardBody(
        [
            html.H2("Overall System Status", style={'text-align': 'center'}),
            html.Div(id='node-status-display'),
            html.H2("Latest Information", className="card-title",
                    style={"width": "50%", "height": "500px", "position": "absolute", "top": "200px",
                           "right": "0px", 'text-align': 'center'}, ),
            latest_info(),
            html.H2("Central Hub Collected Data", style={'position': 'absolute', 'top': '200px', 'left': '10px'}),
            generate_table(),
        ]
    ),
    className="mt-3",
)

tab2_content = dbc.Card(
    dbc.CardBody(
        [
            dcc.Graph(
                id='fire-severity-graph',
                figure=update_fire_severity_graph(1),
                style={"width": "100%", "height": "800px", 'position': 'absolute', 'top': '0px', 'left': '0px',
                       'text-align': 'center'},
            ),

        ]
    ),
    className="mt-3",
)

tab3_content = dbc.Card(
    dbc.CardBody([
        html.H4("Logged History", className="card-title", style={'textAlign': 'center'}),
        html.P("Select a date to download the history of fire severity logs.", style={'textAlign': 'center'}),
        dbc.Row(
            dbc.Col(
                dcc.DatePickerSingle(
                    id='date-picker-single',
                    min_date_allowed=datetime.date(2021, 1, 1),  # adjust based on your data
                    max_date_allowed=datetime.date.today(),
                    date=datetime.date.today(),
                    display_format='YYYY-MM-DD',
                    style={'margin': 'auto'}
                ),
                width=1,  # Adjusted for the date picker width
                className='mb-3',  # Margin bottom for spacing
                align='center'  # Align center for vertical alignment
            ),
            justify='center'  # Horizontally center the column in the row
        ),
        dbc.Row(
            dbc.Col(
                dbc.Button(
                    children=[
                        html.I(className="fas fa-download mr-2"),  # using Font Awesome icons
                        "Download Logged History"
                    ],
                    id="download-btn",
                    color="info",
                    className="btn-block",
                    n_clicks=0
                ),
                width=1,  # Adjusted for the button width
                align='center'  # Align center for vertical alignment
            ),
            justify='center'  # Horizontally center the column in the row
        ),
        dcc.Download(id="download-csv")
    ]),
    className="mt-3",
    style={'box-shadow': '0px 0px 10px #aaa'}
)

test_png = './assets/Prienai_forest.png'
test_base64 = base64.b64encode(open(test_png, 'rb').read()).decode('ascii')

theme_switch = ThemeSwitchAIO(aio_id="theme", themes=[dbc.themes.SLATE, dbc.themes.PULSE])

# App layout
app.layout = html.Div([
    html.H1(["Nature Guard Monitoring System"], style={'text-align': 'center'}),
    html.H5(theme_switch, style={'text-align': 'center'}),
    dcc.Interval(id='update-interval', interval=5000, n_intervals=0),  # Updates the badge periodically
    dbc.Button("Notifications", id="notification-button", color="primary", n_clicks=0,
               style={'position': 'absolute', 'top': '85px', 'right': '0px'}),
    popover,
    dbc.Tabs(
        [
            dbc.Tab(tab1_content, label="Main Hub", label_style={"color": 'Red'},
                    active_label_style={"color": "Green"}),
            dbc.Tab(tab2_content, label="Data Visualization", label_style={"color": 'Red'},
                    active_label_style={"color": "Green"}),
            dbc.Tab(tab3_content, label="Logged History", label_style={"color": 'Red'},
                    active_label_style={"color": "Green"}),
        ]
    ),
])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
