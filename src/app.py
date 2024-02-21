import dash
from dash import dcc, html
import pandas as pd

# Sample data
data = {
    'Name': ['John', 'Alice', 'Bob', 'Carol'],
    'Age': [25, 30, 35, 40],
    'City': ['New York', 'Los Angeles', 'Chicago', 'Houston']
}

df = pd.DataFrame(data)

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

# Define the layout of the app
app.layout = html.Div([
    html.H1('Table Display'),
    dcc.Graph(
        id='table',
        figure={
            'data': [
                {
                    'type': 'table',
                    'header': {
                        'values': df.columns
                    },
                    'cells': {
                        'values': df.values.tolist(),
                    }
                }
            ]
        }
    )
])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True,port=8071)
