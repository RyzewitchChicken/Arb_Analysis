from dash import Dash, html, dcc, callback, Output, Input, State,dash_table
import plotly.express as px
import pandas as pd
import openpyxl
import plotly.graph_objects as go
import base64
import datetime
import io

app = Dash(__name__)
server= app.server
data={}

def remove_strikethrough_cells(df,filename):
    if filename.endswith('.xlsx'):
        workbook = openpyxl.load_workbook(io.BytesIO(df))
        sheet = workbook.active

        for row in sheet.iter_rows():
            for cell in row:

                if cell.font and cell.font.strike:
                    cell.value = None
        data=list(sheet.values)
        df=pd.DataFrame(data[1:], columns=data[0])

    return df
    
    #print(f"File saved as '{output_file}' with strikethrough cells removed.")



def find_arbitrage(df, home1, away1, home2, away2, result_col):

    def calculate_arbitrage(row):
        combined_odds_1 = (1 / row[home2] + 1 / row[away1])*100
        combined_odds_2 = (1 / row[home1] + 1 / row[away2])*100

        if combined_odds_1 < 100:
            return combined_odds_1
        elif combined_odds_2 < 100:
            return combined_odds_2
        else:
            return 100

    df[result_col] = df.apply(calculate_arbitrage, axis=1)

    return df


def get_unique_base_names(df):
    base_names = [col.split(' ', 1)[-1] for col in df.columns]
    remove=['Timestamp', 'score']
    unique_base_names = list(set(base_names))
    unique_base_names = [x for x in unique_base_names if x not in remove]
    
    return unique_base_names

def get_combined_dataframe(selection_1, selection_2, df):
    selected_columns_1 = [col for col in df.columns if col.endswith(selection_1)]
    selected_columns_2 = [col for col in df.columns if col.endswith(selection_2)]
    
    # Ensure Timestamp is always included
    combined_columns = ['Timestamp'] + selected_columns_1 + selected_columns_2
    
    if len(combined_columns) > 1:
        return df[combined_columns]
    else:
        return None, f"Error filtering"



# Requires Dash 2.17.0 or later
app.layout = html.Div([
    html.H1(children='Arb Analysis', style={'textAlign':'center'}),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # Allow multiple files to be uploaded
        multiple=False
    ),
    html.Div(id='output-data-upload'),
    html.Div(id='selectors-container'),
    #html.Div(id='selected-columns-output'),
    dcc.Graph(figure={},id="arb_chart"),
    html.Div(id='arb-count', style={'margin-top': '20px', 'font-weight': 'bold', 'font-size': '16px'})
    #dcc.Graph(figure= fig)
])
def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif filename.endswith('.xlsx'):
            df = remove_strikethrough_cells(decoded, filename)
        else:
            return None, f"Unsupported file format: {filename}"
        return df, filename
    except Exception as e:
        return None, str(e)
    

@callback([Output('output-data-upload', 'children'),Output('selectors-container', 'children')],
              Input('upload-data', 'contents'),
              State('upload-data', 'filename'))


def update_output(contents,filename):
    global data
    df, error_message = parse_contents(contents, filename)
    if df is not None:
        data= df
        unique_names=get_unique_base_names(df)
        column_options = [{'label': col, 'value': col} for col in unique_names]
        
        return html.Div([
            html.H5(f"File Name: {filename}"),
            html.H5("Column Names:"),
            html.Ul([html.Li(col) for col in df.columns])

        ]), html.Div([
            html.Div([
                html.Label("Select Bookie:", style={'display': 'block', 'margin-bottom': '5px'}),
                dcc.Dropdown(id='column-selector-1', options=column_options, placeholder='Select Bookie', style={'width': '100%'})
            ], style={'display': 'inline-block', 'width': '48%', 'vertical-align': 'top', 'margin-right': '10px'}),
            html.Div([
                html.Label("Select Bookie:", style={'display': 'block', 'margin-bottom': '5px'}),
                dcc.Dropdown(id='column-selector-2', options=column_options, placeholder='Select Bookie', style={'width': '100%'})
            ], style={'display': 'inline-block', 'width': '48%', 'vertical-align': 'top'})
        ], style={'display': 'flex'})
    else:
        return html.Div(f"Error: {error_message}")
    


@callback([Output('arb_chart', 'figure'),Output('arb-count','children')],
              [Input('column-selector-1', 'value'),
              Input('column-selector-2', 'value')])


def update_chart(drop1, drop2):
    
    #set_columns=['Timestamp','ML-ML1 Betsson','ML-ML2 Betsson']
    #arbcompare = data[ set_columns + [col for col in data.columns if drop1  in col] + [col for col in data.columns if drop2  in col]]
    arbcompare= get_combined_dataframe(drop1,drop2,data)
    arbcompare=arbcompare[~(arbcompare == 0).any(axis=1)]
    arbcompare=arbcompare.dropna()
    arbcompare=find_arbitrage(arbcompare, arbcompare.columns[1], arbcompare.columns[2], arbcompare.columns[3], arbcompare.columns[4], 'arbbb')
        # Initialize figure
    print(arbcompare)

#fig.add_trace(go.Scatter(x=event_data['Timestamp'],y=event_data['ML-ML2 Betsson'],mode='markers',marker=dict(size=8, color='red', symbol='circle'),name="Arbing"))
    fig = go.Figure()
    ranges = [(98, 99), (95, 97), (90, 94)]
    colors = ['#6E6969', '#A19E9E','#080000']
    # Initialize figure


    #event_data = arbcompare[arbcompare['arbbb'] < 98 & arbcompare['arbbb'] > 99]
    for column in arbcompare.columns:
        if column != 'arbbb' and column != 'Timestamp':
            fig.add_trace(go.Scatter(x=arbcompare['Timestamp'],y=arbcompare[column],name=column))
    arbs=0
    for i,r in enumerate(ranges):
        # Filter data for the range
        event_data = arbcompare[(arbcompare['arbbb'] > r[0]) & (arbcompare['arbbb'] < r[1])]
        # Add trace to the figure
        fig.add_trace(go.Scatter(x=event_data['Timestamp'], y=event_data.iloc[:, 2], mode='markers', marker=dict(size=8, color=colors[i], symbol='circle'),
                                name=f"Arb {100-r[1]}% -{100-r[0]}%"))
        #print(event_data.shape[0])
        
        arbs+=event_data.shape[0]
        time_changes=event_data
        time_changes = time_changes.sort_values(by='Timestamp')
        time_changes['time_diff']=time_changes['Timestamp'].diff().dt.total_seconds()
        time_changes['Value_Changed'] = time_changes.iloc[:,1].diff().ne(0)  

        
        groups = (time_changes['Value_Changed']).cumsum()  
        #print(time_changes)

        grouped_df = time_changes.groupby(groups).filter(lambda x: x['Timestamp'].iloc[-1] - x['Timestamp'].iloc[0] >= pd.Timedelta(seconds=20))
        start_times = grouped_df[grouped_df['Value_Changed'] | grouped_df.index == 0]['Timestamp'].tolist()
        #print(grouped_df)
        #print(grouped_df[['Timestamp', 'ML-ML1 Betsson']])
        #print(grouped_df)
        if not grouped_df.empty:
            start_times = []
            end_times = []

            # Track the first row
            prev_value = grouped_df.iloc[0,1]
            start_time = grouped_df['Timestamp'].iloc[0]

            # Iterate through the dataframe to find stable periods
            for i in range(1, len(grouped_df)):
                current_value = grouped_df.iloc[i,1]
                
                # If the value changes, store the previous stable period
                if current_value != prev_value:
                    end_times.append(grouped_df['Timestamp'].iloc[i - 1])  # The previous row is the last of stable period
                    start_times.append(start_time)  # Store start time
                    
                    # Update new period
                    start_time = grouped_df['Timestamp'].iloc[i]
                    prev_value = current_value

            # Capture the last stable period
            start_times.append(start_time)
            end_times.append(grouped_df['Timestamp'].iloc[-1])
            print(start_times)
            print(end_times)
            for start, end in zip(start_times, end_times):
                fig.add_vrect(x0=start, x1=end, fillcolor="gray", opacity=0.4, line_width=0)        

    
    


    count_text = f"Number of arb count: {arbs}"  
     
    #fig.add_trace(go.Scatter(x=event_data['Timestamp'],y=event_data['ML-ML2 Betsson'],mode='markers',marker=dict(size=8, color='red', symbol='circle'),name="Arbing"))
    fig.update_layout(title='Odds movement',
                    xaxis_title='Timestamp',
                    yaxis_title='Odds')

    return  fig, count_text




if __name__ == '__main__':
    app.run(debug=True)
