from shiny import App, render, ui
import altair as alt
import pandas as pd
from shinywidgets import render_altair, output_widget
import json

# Load the data
collapsed_df = pd.read_csv('/Users/georgew/Desktop/Fall 2024/PPHA 30538/pset6_george_wang/top_alerts_map_byhour/top_alerts_map_byhour.csv')
coordinates_df = pd.read_csv('/Users/georgew/Desktop/Fall 2024/PPHA 30538/pset6_george_wang/coordinates_df.csv')

# Load the JSON data
file_path = "/Users/georgew/Desktop/Fall 2024/PPHA 30538/pset6_george_wang/top_alerts_map/chicago-boundaries.geojson"
with open(file_path) as f:
    chicago_geojson = json.load(f)
geo_data = alt.Data(values=chicago_geojson["features"])

# Extract unique type and subtype combinations
type_subtype_choices = collapsed_df['updated_type'] + " - " + collapsed_df['updated_subtype']
type_subtype_choices = type_subtype_choices.unique()

# Define the UI
app_ui = ui.page_fluid(
    ui.panel_title("PS6 App2"),
    ui.input_select(
        "type_subtype",
        "Select Type and Subtype",
        choices=list(type_subtype_choices),
        selected=type_subtype_choices[0]
    ),
    ui.input_select(
        "hour", 
        "Select Hour", 
        choices=[f"{str(h).zfill(2)}:00" for h in range(24)],  # Format hours as HH:00
        selected="12:00"
    ),
    output_widget("combined_plot")
)

# Define the server logic
def server(input, output, session):
    @render_altair
    def combined_plot():
        # Get user-selected inputs
        selected_type_subtype = input.type_subtype()
        chosen_type, chosen_subtype = selected_type_subtype.split(" - ")
        selected_hour = input.hour()  # Get the hour in HH:00 format

        # Filter corresponding data
        filtered_df = collapsed_df[
            (collapsed_df['updated_type'] == chosen_type) &
            (collapsed_df['updated_subtype'] == chosen_subtype) &
            (collapsed_df['hour'] == selected_hour)
        ]

        if filtered_df.empty:
            print("No data available for the selected filters.")
            return alt.Chart().mark_text(
                text="No data available for this selection",
                align='center',
                baseline='middle',
                fontSize=16
            ).properties(width=400, height=300)

        # Parse lat_long_bin into latitude_bin and longitude_bin
        filtered_df = filtered_df[filtered_df['lat_long_bin'].notnull()]  # Filter non-null bins
        filtered_df[['latitude_bin', 'longitude_bin']] = pd.DataFrame(
            filtered_df['lat_long_bin'].apply(
                lambda x: list(map(float, x.strip('()').split(',')))
            ).tolist(),
            index=filtered_df.index
        )

        # Create the scatter plot
        scatter_plot = alt.Chart(filtered_df).mark_circle().encode(
            x=alt.X('longitude_bin:Q', title='Longitude', scale=alt.Scale(domain=[-87.95, -87.5])),
            y=alt.Y('latitude_bin:Q', title='Latitude', scale=alt.Scale(domain=[41.6, 42.1])),
            size=alt.Size('count:Q', title='Number of Alerts'),
            tooltip=['latitude_bin', 'longitude_bin', 'count']
        ).properties(
            title=f'Top 10 Bins of Alerts at {selected_hour}',
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

        combined_plot = base_map + scatter_plot

        return combined_plot

# Create the app
app = App(app_ui, server)
