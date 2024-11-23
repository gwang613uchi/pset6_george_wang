from shiny import App, render, ui
import pandas as pd
import altair as alt
from shinywidgets import render_altair, output_widget
import json

# Open and load the geojson
file_path = "/Users/georgew/Desktop/Fall 2024/PPHA 30538/pset6_george_wang/top_alerts_map/chicago-boundaries.geojson"
with open(file_path) as f:
    chicago_geojson = json.load(f)

geo_data = alt.Data(values=chicago_geojson["features"])

# Create the base map using the GeoJSON data
base_map = alt.Chart(geo_data).mark_geoshape(
    fill='lightgray',
    stroke='black'
).encode(
    tooltip=['properties.name:N']
).project(
    type='equirectangular'
).properties(
    width=400,
    height=300
)

# Load the data
df = pd.read_csv('/Users/georgew/Desktop/Fall 2024/PPHA 30538/pset6_george_wang/merged_data.csv')
coordinates_df = pd.read_csv('/Users/georgew/Desktop/Fall 2024/PPHA 30538/pset6_george_wang/coordinates_df.csv')

# Extract unique type and subtype combinations
type_subtype_choices = df['updated_type'] + " - " + df['updated_subtype']
type_subtype_choices = type_subtype_choices.unique()

# UI Side
app_ui = ui.page_fluid(
    ui.panel_title("PS 6"),
    ui.input_select(
        "type_subtype", 
        "Select Type and Subtype", 
        choices=list(type_subtype_choices), 
        selected=type_subtype_choices[0]
    ),
    output_widget("combined_plot"),
    ui.input_switch("hour_filter", "Filter by Hour", value=False),
    ui.panel_conditional("input.hour_filter == true",
        ui.input_slider("hour", "Select Hour", min=0, max=23, value=12)),
    ui.panel_conditional("input.hour_filter == false",
        ui.input_slider("hour_range", "Select Hour Range", min=0, max=23, value=[0, 23]))
)

# Server Side
def server(input, output, session):
    @render_altair
    def combined_plot():
        selected_type_subtype = input.type_subtype()
        chosen_type, chosen_subtype = selected_type_subtype.split(" - ")

        # Filter the data for the chosen type and subtype
        filtered_df = df[(df['updated_type'] == chosen_type) & (df['updated_subtype'] == chosen_subtype)]

        # Aggregate the data to find the top 10
        top_alerts = coordinates_df.loc[filtered_df.index].groupby('lat_long_bin').size().reset_index(name='count')
        top_10_alerts = top_alerts.nlargest(10, 'count')

        # Debugging: Print the top 10 alerts
        print(top_10_alerts)

        # Extract latitude and longitude from the bins
        top_10_alerts[['latitude_bin', 'longitude_bin']] = pd.DataFrame(
            top_10_alerts['lat_long_bin'].apply(lambda x: list(map(float, x.strip('()').split(',')))).tolist(),
            index=top_10_alerts.index
        )

        # Debugging: Print the DataFrame with latitude and longitude
        print(top_10_alerts)

        # Create the scatter plot
        scatter_plot = alt.Chart(top_10_alerts).mark_circle().encode(
            x=alt.X('longitude_bin:Q', title='Longitude', scale=alt.Scale(domain=[-87.95, -87.5])),
            y=alt.Y('latitude_bin:Q', title='Latitude', scale=alt.Scale(domain=[41.6, 42.1])),
            size=alt.Size('count:Q', title='Number of Alerts'),
            tooltip=['latitude_bin', 'longitude_bin', 'count']
        ).properties(
            title=f'Top 10 Latitude-Longitude Bins with Highest Number of "{selected_type_subtype}" Alerts',
            width=400,
            height=300
        )
        
        # Create the base map using the GeoJSON data
        base_map = alt.Chart(geo_data).mark_geoshape(
            fill='lightgray',
            stroke='black'
        ).encode(
            tooltip=['properties.name:N']
        ).project(
            type='equirectangular'
        ).properties(
            width=400,
            height=300
        )

        # Layer the scatter plot on top of the base map
        combined_plot = base_map + scatter_plot

        return combined_plot

app = App(app_ui, server)
