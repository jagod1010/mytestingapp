import dash
from dash import html, dcc
from dash.dependencies import Input, Output
from firebase import firebase
import dash_table

# Initialize the Dash app
app = dash.Dash(__name__)

# Initialize Firebase with your Firebase project credentials
firebase = firebase.FirebaseApplication('https://central-hub-7fe3e-default-rtdb.firebaseio.com/', None)

# Define the layout of the app
app.layout = html.Div([
    html.H1('Live Data Table'),
    dash_table.DataTable(
        id='table',
        columns=[
            {'name': 'Timestamp', 'id': 'timestamp'},
            {'name': 'Value', 'id': 'value'}
        ],
        page_size=10
    ),
    dcc.Interval(
        id='interval-component',
        interval=5000,  # Update data every 5 seconds
        n_intervals=0
    )
])

# Define callback to update table data
@app.callback(
    Output('table', 'data'),
    [Input('interval-component', 'n_intervals')]
)
def update_table(n):
    # Fetch data from Firebase
    data = firebase.get('/lora_data', None)

    # Process fetched data and format it for the table
    table_data = [{'timestamp': entry['timestamp'], 'value': entry['value']} for entry in data.values()]

    return table_data

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
