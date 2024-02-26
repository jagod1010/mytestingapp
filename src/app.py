import dash
from dash import html, dcc
from dash.dependencies import Input, Output
from firebase import firebase
from dash import dash_table
from dash.dash_table.Format import Group
import datetime
from dash import Dash, html, dcc, Input, Output, callback
import pandas as pd
import dash_ag_grid as dag
import base64
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import ThemeSwitchAIO
import plotly.express as px
import plotly.graph_objs as go

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

# Initialize Firebase with your Firebase project credentials
firebase = firebase.FirebaseApplication('https://central-hub-7fe3e-default-rtdb.firebaseio.com/', None)

# Define column definitions for dash_ag_grid
columnDefs = [
    {"field": "timestamp", "name": "Timestamp"},
    {"field": "average_temperature", "name": "Average Temperature"},
    {"field": "compass", "name": "Compass"},
    {"field": "angle", "name": "Angle"},
    {"field": "fire_severity", "name": "Fire Severity"},
]


def parse_temperature(temp_str):
    # Remove the 'C' and any surrounding whitespace, then convert to float
    return float(temp_str.replace('C', '').strip())


# Callback to update the graph
@app.callback(
    Output('fire-severity-graph', 'figure'),  # The ID of your graph component
    [Input('interval-component', 'n_intervals')]
)
def update_fire_severity_graph(n):
    # Fetch data from Firebase
    # Uncomment and configure the following line if you're using Firebase Admin SDK
    # data = db.collection(u'lora_data').stream()

    # For now, we'll simulate fetching data as a list of dictionaries
    # Replace the following line with actual data fetching from Firebase
    data_graph = firebase.get('/lora_data', None)

    # Prepare the data for plotting
    timestamps = []
    avg_temperatures = []
    fire_severities = []

    for key, entry in data_graph.items():
        value_components = entry['value'].split(', ')
        timestamp = datetime.datetime.fromtimestamp(entry['timestamp'])
        avg_temperature_str = value_components[2].split(':')[1]
        fire_severity_str = value_components[4].split(':')[1]

        # Parse the temperature and severity values
        avg_temperature = parse_temperature(avg_temperature_str)
        fire_severity = float(fire_severity_str.replace('%', '').strip())  # Remove the '%' and convert to float

        timestamps.append(timestamp)
        avg_temperatures.append(avg_temperature)
        fire_severities.append(fire_severity)

    # Create the figure
    fig = go.Figure(layout_template='plotly_dark')

    # Add traces
    fig.add_trace(go.Scatter(x=timestamps, y=avg_temperatures, name='Average Temperature', mode='lines+markers'))
    fig.add_trace(go.Scatter(x=timestamps, y=fire_severities, name='Fire Severity', mode='lines+markers', yaxis='y2'))

    # Update layout for the second y-axis
    fig.update_layout(
        title='Fire Severity and Average Temperature Over Time',
        yaxis_title='Average Temperature (°C)',
        yaxis2=dict(
            title='Fire Severity (%)',
            overlaying='y',
            side='right'
        ),
        xaxis_title='Time'
    )

    return fig


# Define a function to generate badges based on node status
def generate_node_status_content(nodes_status):
    return html.Ul([
        html.Li([
            html.Span(f"{node['name']}: ", style={'font-size': '20px'}),  # Customize font size here
            dbc.Badge("ON", color="success") if node['status'] == 'on' else dbc.Badge("OFF", color="danger")
        ]) for node in nodes_status
    ], style={'list-style-type': 'none'})  # Optionally remove bullet points


# Simulated node status data
nodes_status = [
    {'name': 'NODE 1', 'status': 'on'},
    {'name': 'NODE 2', 'status': 'off'},
    {'name': 'CENTRAL HUB', 'status': 'on'},
]


def generate_table():
    return html.Ul([
        dbc.Button("Download Data", id="csv-button", n_clicks=0,
                   style={'position': 'absolute', 'top': '250px', 'left': '10px'}),
        dag.AgGrid(
            id='table',
            columnDefs=columnDefs,
            columnSize="sizeToFit",
            defaultColDef={"filter": True, "sortable": True},
            dashGridOptions={"pagination": True, "animateRows": True},
            style={"width": "50%", "height": "500px", 'position': 'absolute', 'top': '300px', 'left': '0px'},
            csvExportParams={
                "fileName": "ag_grid_test.csv",
            },
            className="ag-theme-quartz-dark",

        ),
        dcc.Interval(
            id='interval-component',
            interval=5000,  # in milliseconds
            n_intervals=0
        )
    ])


tab1_content = dbc.Card(
    dbc.CardBody(
        [
            html.H2("Overall System Status:"),
            generate_node_status_content(nodes_status),

            html.H2("Central Hub Collected Data:", style={'position': 'absolute', 'top': '200px', 'left': '10px'}),
            generate_table(),
            dcc.Graph(
                id='fire-severity-graph',
                figure=update_fire_severity_graph(1),  # fig is a Plotly figure object created using go.Figure()
                style={"width": "50%", "height": "500px", 'position': 'absolute', 'top': '300px', 'right': '0px'},
            ),
        ]
    ),
    className="mt-3",
)

# Update tab2_content to include badges for node status
tab2_content = dbc.Card(
    dbc.CardBody(
        [
            html.H2("TBD:"),

        ]
    ),
    className="mt-3",
)
test_png = './assests/Prienai_forest.png'
test_base64 = base64.b64encode(open(test_png, 'rb').read()).decode('ascii')

# Define the ThemeSwitchAIO component for theme toggling
theme_switch = ThemeSwitchAIO(aio_id="theme", themes=[dbc.themes.SLATE, dbc.themes.PULSE])
app.layout = html.Div([
    html.H1(["Nature Guard Monitoring System"]),
    theme_switch,
    dbc.Tabs(
        [
            dbc.Tab(tab1_content, label="Main Hub", label_style={"color": 'Red'},
                    active_label_style={"color": "Green"}),
            dbc.Tab(tab2_content, label="TB", label_style={"color": 'Red'},
                    active_label_style={"color": "Green"}),
        ]
    ),
])


@app.callback(
    Output('table', 'rowData'),
    [Input('interval-component', 'n_intervals')]
)
def update_table(n):
    # Fetch data from Firebase
    data = firebase.get('/lora_data', None)

    table_data = []
    for key, entry in data.items():
        value_components = entry['value'].split(', ')
        timestamp = entry['timestamp']
        timestamp = datetime.datetime.fromtimestamp(timestamp)
        timestamp_with_suffix = timestamp.strftime('%Y-%m-%d %I:%M:%S %p')
        avg_temperature = value_components[2].split(':')[1]
        compass = value_components[1].split(':')[1]
        angle = value_components[3].split(':')[1]
        fire_severity = value_components[4].split(':')[1]

        table_data.append({
            'timestamp': timestamp_with_suffix,
            'average_temperature': avg_temperature,
            'compass': compass,
            'angle': angle,
            'fire_severity': fire_severity
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


# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
