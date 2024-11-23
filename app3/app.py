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

# Convert 'hour' column to integer (e.g., '00:00' -> 0, '01:00' -> 1)
collapsed_df['hour_int'] = collapsed_df['hour'].str.split(':').str[0].astype(int)

# Define the UI
app_ui = ui.page_fluid(
    ui.panel_title("PS6 App3"),
    ui.input_select(
        "type_subtype",
        "Select Type and Subtype",
        choices=list(type_subtype_choices),
        selected=type_subtype_choices[0]
    ),
    ui.input_switch("hour_filter", "Toggle to switch to range of hours", value=False),
    ui.panel_conditional(
        "input.hour_filter == false",
        ui.input_slider("hour", "Select Hour", min=0, max=23, value=12)
    ),
    ui.panel_conditional(
        "input.hour_filter == true",
        ui.input_slider("hour_range", "Select Hour Range", min=0, max=23, value=[0, 23])
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
        hour_filter = input.hour_filter()

        if hour_filter:
            selected_hour_range = input.hour_range()
            filtered_df = collapsed_df[
                (collapsed_df['updated_type'] == chosen_type) &
                (collapsed_df['updated_subtype'] == chosen_subtype) &
                (collapsed_df['hour_int'].between(selected_hour_range[0], selected_hour_range[1]))
            ]
        else:
            selected_hour = input.hour()
            filtered_df = collapsed_df[
                (collapsed_df['updated_type'] == chosen_type) &
                (collapsed_df['updated_subtype'] == chosen_subtype) &
                (collapsed_df['hour_int'] == selected_hour)
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
        filtered_df['latitude_bin'], filtered_df['longitude_bin'] = zip(
            *filtered_df['lat_long_bin'].apply(
                lambda x: tuple(map(float, x.strip("()").split(",")))
            )
        )

        # Aggregate data for the selected hour range
        aggregated_df = filtered_df.groupby('lat_long_bin').agg({'count': 'sum'}).reset_index()

        # Extract latitude and longitude directly from the tuple
        aggregated_df[['latitude_bin', 'longitude_bin']] = pd.DataFrame(
            aggregated_df['lat_long_bin'].apply(lambda x: list(map(float, x.strip("()").split(",")))).tolist(),
            index=aggregated_df.index
        )

        # Select top 10 bins based on counts
        top_10_bins = aggregated_df.nlargest(10, 'count')

        # Create the scatter plot
        scatter_plot = alt.Chart(top_10_bins).mark_circle().encode(
            x=alt.X('longitude_bin:Q', title='Longitude', scale=alt.Scale(domain=[-87.95, -87.5])),
            y=alt.Y('latitude_bin:Q', title='Latitude', scale=alt.Scale(domain=[41.6, 42.1])),
            size=alt.Size('count:Q', title='Number of Alerts'),
            tooltip=['latitude_bin', 'longitude_bin', 'count']
        ).properties(
            title=f'Top 10 Bins of Alerts ({selected_hour_range[0]}:00-{selected_hour_range[1]}:00)' if hour_filter else f'Top 10 Bins of Alerts ({selected_hour}:00)',
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
