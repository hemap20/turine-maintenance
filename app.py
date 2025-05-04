import dash
from dash import dcc, html, Input, Output
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Load data
df = pd.read_csv("turbine_sensor_data.csv", parse_dates=['timestamp'])
df.sort_values('timestamp', inplace=True)

# Detect anomalies
window = 24
for col in ['temperature', 'pressure', 'vibration']:
    rolling_mean = df[col].rolling(window).mean()
    rolling_std = df[col].rolling(window).std()
    df[f'{col}_zscore'] = (df[col] - rolling_mean) / rolling_std
    df[f'{col}_anomaly'] = (df[f'{col}_zscore'].abs() > 3).astype(int)

# Initialize Dash
app = dash.Dash(__name__, title="Dark Turbine Dashboard")
app.title = "Turbine Sensor Monitor"

app.layout = html.Div(
    style={'backgroundColor': '#1e1e1e', 'color': 'white', 'padding': '20px'},
    children=[
        html.H1("Turbine Predictive Maintenance", style={'textAlign': 'center'}),

        dcc.Dropdown(
            id='sensor-select',
            options=[{'label': s.capitalize(), 'value': s} for s in ['temperature', 'pressure', 'vibration']],
            value='temperature',
            style={'width': '40%', 'margin': 'auto', 'color': '#000'}
        ),
        
        html.Div([
            dcc.Graph(id='trend-plot'),
            dcc.Graph(id='heatmap-plot'),
            dcc.Graph(id='zscore-boxplot'),
            dcc.Graph(id='anomaly-bar'),
            dcc.Graph(id='rolling-mean-trend'),
            dcc.Graph(id='sensor-distribution'),
            dcc.Graph(id='daily-kpi-summary')
        ])
    ]
)

@app.callback(
    [Output('trend-plot', 'figure'),
     Output('heatmap-plot', 'figure'),
     Output('zscore-boxplot', 'figure'),
     Output('anomaly-bar', 'figure'),
     Output('rolling-mean-trend', 'figure'),
     Output('sensor-distribution', 'figure'),
     Output('daily-kpi-summary', 'figure')],
    [Input('sensor-select', 'value')]
)
def update_dashboard(sensor):
    # 1. Trend with anomaly highlights
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df['timestamp'], y=df[sensor],
        mode='lines', name=sensor.capitalize(),
        line=dict(width=2)
    ))
    fig1.add_trace(go.Scatter(
        x=df['timestamp'][df[f'{sensor}_anomaly'] == 1],
        y=df[sensor][df[f'{sensor}_anomaly'] == 1],
        mode='markers', name='Anomaly',
        marker=dict(color='red', size=6, symbol='x')
    ))
    fig1.update_layout(
        template='plotly_dark', title=f"{sensor.capitalize()} Over Time",
        xaxis_title='Time', yaxis_title=sensor.capitalize()
    )

    # 2. Heatmap (Hour vs Day)
    df_hm = df.copy()
    df_hm['hour'] = df_hm['timestamp'].dt.hour
    df_hm['day'] = df_hm['timestamp'].dt.date
    heatmap = df_hm.pivot_table(index='hour', columns='day', values=sensor)
    fig2 = px.imshow(
        heatmap, aspect='auto', origin='lower',
        title=f"{sensor.capitalize()} Heatmap (Hour vs Day)",
        color_continuous_scale='Viridis'
    )
    fig2.update_layout(template='plotly_dark')

    # 3. Z-score Boxplot
    fig3 = px.box(df, y=f'{sensor}_zscore', points="all", title=f"{sensor.capitalize()} Z-score Distribution")
    fig3.update_layout(template='plotly_dark')

    # 4. Anomaly count bar
    daily_anomalies = df.copy()
    daily_anomalies['date'] = daily_anomalies['timestamp'].dt.date
    anomaly_counts = daily_anomalies.groupby('date')[f'{sensor}_anomaly'].sum().reset_index()
    fig4 = px.bar(anomaly_counts, x='date', y=f'{sensor}_anomaly',
                  title=f"Daily Anomaly Count for {sensor.capitalize()}")
    fig4.update_layout(template='plotly_dark', xaxis_title="Date", yaxis_title="Anomaly Count")

    # 5. Rolling mean with band
    rolling = df[sensor].rolling(window)
    mean = rolling.mean()
    std = rolling.std()
    fig5 = go.Figure([
        go.Scatter(x=df['timestamp'], y=df[sensor], name='Raw', mode='lines'),
        go.Scatter(x=df['timestamp'], y=mean, name='Rolling Mean'),
        go.Scatter(x=df['timestamp'], y=mean + std, name='+1 STD', line=dict(dash='dot')),
        go.Scatter(x=df['timestamp'], y=mean - std, name='-1 STD', line=dict(dash='dot')),
    ])
    fig5.update_layout(title=f"{sensor.capitalize()} Rolling Stats", template='plotly_dark')

    # 6. Distribution histogram + KDE
    fig6 = px.histogram(df, x=sensor, nbins=40, marginal="violin", opacity=0.8,
                        title=f"{sensor.capitalize()} Distribution + KDE", histnorm="probability")
    fig6.update_layout(template='plotly_dark')

    # 7. KPI summary (min, max, mean)
    daily_kpi = df.groupby(df['timestamp'].dt.date)[sensor].agg(['min', 'mean', 'max']).reset_index()
    fig7 = go.Figure()
    fig7.add_trace(go.Scatter(x=daily_kpi['timestamp'], y=daily_kpi['mean'], name='Mean'))
    fig7.add_trace(go.Scatter(x=daily_kpi['timestamp'], y=daily_kpi['max'], name='Max'))
    fig7.add_trace(go.Scatter(x=daily_kpi['timestamp'], y=daily_kpi['min'], name='Min'))
    fig7.update_layout(template='plotly_dark', title=f"Daily {sensor.capitalize()} Summary", xaxis_title='Date')

    return fig1, fig2, fig3, fig4, fig5, fig6, fig7

if __name__ == '__main__':
    app.run(debug=True)
