# app.py
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
from sqlalchemy import create_engine, text
from dash import dash_table

# Database Connection Parameters
DB_NAME = "bot"
DB_USER = "avnadmin"
DB_PASSWORD = "AVNS_lNZeFxak5N49NDPs5hh"
DB_HOST = "pg-209c89ad-nathan-37e1.e.aivencloud.com"
DB_PORT = "10497"

# SQLAlchemy Engine for DataFrame loading
DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(DATABASE_URL)

def get_table_names():
    with engine.connect() as connection:
        result = connection.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        return [row[0] for row in result]

def load_data(table_name):
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, engine)
    return df

def load_crypto_data():
    query = """
    SELECT 
        pair_address, 
        base_token_name, 
        price, 
        liquidity, 
        volume_24h, 
        chain, 
        exchange,
        created_at
    FROM pairs
    ORDER BY volume_24h DESC
    LIMIT 100
    """
    return pd.read_sql(query, engine)

# Initialize Dash App
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# App Layout
app.layout = html.Div([
    html.H1("Database Analytics & Crypto Viability Dashboard", style={'textAlign': 'center'}),
    
    # Table Selection
    html.Div([
        html.Label('Select Table:'),
        dcc.Dropdown(
            id='table-dropdown',
            options=[{'label': table, 'value': table} for table in get_table_names()],
            value=get_table_names()[0] if get_table_names() else None
        )
    ], style={'padding': '20px', 'width': '50%'}),
    
    # Tabs for different views
    dcc.Tabs([
        dcc.Tab(label='Table Data', children=[
            html.Div(id='table-display')
        ]),
        dcc.Tab(label='Crypto Viability', children=[
            html.Div([
                dcc.Dropdown(
                    id='chain-dropdown',
                    options=[{'label': chain, 'value': chain} 
                             for chain in load_crypto_data()['chain'].unique()],
                    placeholder='Select Chain'
                ),
                dcc.Graph(id='viability-scatter')
            ])
        ])
    ])
])

# Callback for table display
@app.callback(
    Output('table-display', 'children'),
    [Input('table-dropdown', 'value')]
)
def update_table_display(selected_table):
    if not selected_table:
        return "No table selected"
    
    df = load_data(selected_table)
    
    return dash_table.DataTable(
        id='table-data',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textOverflow': 'ellipsis', 'maxWidth': 0}
    )

# Callback for crypto viability graph
@app.callback(
    Output('viability-scatter', 'figure'),
    [Input('chain-dropdown', 'value')]
)
def update_viability_graph(selected_chain):
    df = load_crypto_data()
    
    if selected_chain:
        df = df[df['chain'] == selected_chain]
    
    # Viability Score Calculation
    df['viability_score'] = (
        df['volume_24h'] / df['volume_24h'].max() * 0.5 +
        df['liquidity'] / df['liquidity'].max() * 0.5
    ) * 100

    fig = px.scatter(
        df, 
        x='volume_24h', 
        y='liquidity',
        color='viability_score',
        size='price',
        hover_name='base_token_name',
        labels={
            'volume_24h': 'Volume (24h)', 
            'liquidity': 'Liquidity', 
            'viability_score': 'Viability Score'
        },
        title='Crypto Pair Viability Analysis'
    )
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)