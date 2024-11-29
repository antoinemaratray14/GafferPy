#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 22 13:31:45 2024

@author: antoinemaratray
"""

import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from statsbombpy import sb
import matplotlib.colors as mcolors
import matplotlib.cm as cm

# Manual mapping of competitions and seasons
COMPETITIONS = {
    38: "🇵🇱Ekstraklasa",
    47: "🇦🇹Bundesliga",
    7: "🇫🇷Ligue 1",
    75: "🇸🇪Allsvenskan",
    108: "🇯🇵J1 League",
    3: "🏴󠁧󠁢󠁥󠁮󠁧󠁿Championship",
    4: "🏴󠁧󠁢󠁥󠁮󠁧󠁿League One",
    76: "🇨🇿Chance Liga",
    10: "🇩🇪2. Bundesliga",
    179: "🇩🇪3. Liga",
    44: "🇺🇸Major League Soccer",
    88: "🇳🇴Eliteserien",
    51: "🏴󠁧󠁢󠁳󠁣󠁴󠁿SPL"
    
}

SEASONS = {
    317: "2024/2025",
    282: "2024",
    281: "2023/2024",
    107: "2023",
    235: "2022/2023",
    106: "2022",
    108: "2021/2022",
    91: "2021",
    90: "2020/2021"
}

# Metrics to display
METRICS = {
    "team_match_op_xg": "Open Play xG",
    "team_match_sp_xg": "Set Piece xG",
    "team_match_ppda": "PPDA",
    "team_match_counter_attacking_shots": "Counter Attacking Shots",
    "team_match_op_shot_distance": "Open Play Shot Distance",
    "team_match_op_shot_distance_conceded": "Open Play Shot Distance Conceded",
    "team_match_fhalf_pressures_ratio": "Pressures in opposition half Ratio",
    "team_match_possession": "Possession Ratio",
    "team_match_np_xg_conceded": "xG Conceded"
}

@st.cache_data
def fetch_manager_data(email, password, competitions, seasons):
    all_manager_data = []
    all_matches = []

    for comp_id, comp_name in competitions.items():
        for season_id, season_name in seasons.items():
            try:
                matches = sb.matches(
                    competition_id=comp_id,
                    season_id=season_id,
                    creds={"user": email, "passwd": password}
                )
                matches["competition"] = comp_name
                matches["season"] = season_name
                all_matches.append(matches)

                manager_data = matches[["home_team", "home_managers", "away_team", "away_managers", "competition", "season"]]
                home_managers = manager_data[["home_team", "home_managers", "competition", "season"]].rename(
                    columns={"home_team": "team_name", "home_managers": "manager"}
                )
                away_managers = manager_data[["away_team", "away_managers", "competition", "season"]].rename(
                    columns={"away_team": "team_name", "away_managers": "manager"}
                )
                all_manager_data.append(pd.concat([home_managers, away_managers]).drop_duplicates())
            except Exception as e:
                st.warning(f"Error fetching data for {comp_name} - {season_name}: {e}")

    return pd.concat(all_manager_data, ignore_index=True), pd.concat(all_matches, ignore_index=True)

@st.cache_data
def fetch_team_stats(email, password, matches, manager_data):
    team_stats = []

    for _, row in manager_data.iterrows():
        team_name = row["team_name"]
        manager_name = row["manager"]

        team_matches = matches[
            ((matches["home_team"] == team_name) & (matches["home_managers"].str.contains(manager_name, na=False))) |
            ((matches["away_team"] == team_name) & (matches["away_managers"].str.contains(manager_name, na=False)))
        ]

        data = []
        for match_id in team_matches["match_id"].unique():
            try:
                team_match = sb.team_match_stats(
                    match_id=match_id,
                    creds={"user": email, "passwd": password}
                )
                team_match = team_match[team_match["team_name"] == team_name]
                if not team_match.empty:
                    data.append(team_match)
            except Exception:
                pass

        if data:
            data = pd.concat(data)
            avg_stats = data.mean(numeric_only=True).to_dict()
            avg_stats["manager"] = manager_name
            avg_stats["team_name"] = team_name
            avg_stats["competition"] = row["competition"]
            avg_stats["season"] = row["season"]
            avg_stats["games_managed"] = len(team_matches)
            team_stats.append(avg_stats)

    return pd.DataFrame(team_stats)

st.title("Manager Analysis with StatsBomb Data")

# Initialize session state for data
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.manager_data = None
    st.session_state.matches = None
    st.session_state.team_stats = None
    st.session_state.cleaned_data = None

# Sidebar Configuration
st.sidebar.title("Configuration")
email = st.sidebar.text_input("Email", placeholder="Enter your StatsBomb email")
password = st.sidebar.text_input("Password", type="password", placeholder="Enter your StatsBomb password")

if email and password:
    selected_competitions = st.sidebar.multiselect("Select Competitions", list(COMPETITIONS.values()), default=list(COMPETITIONS.values())[:1])
    selected_seasons = st.sidebar.multiselect("Select Seasons", list(SEASONS.values()), default=list(SEASONS.values())[:1])
    
    st.sidebar.slider("Minimum Matches Managed", 1, 50, 5, 1, key="min_matches")
    st.sidebar.slider("Open Play xG Range", 0.0, 3.0, (0.0, 3.0), 0.1, key="op_xg_range")
    st.sidebar.slider("Set Piece xG", 0.0, 1.0, (0.0, 1.0), 0.05, key="sp_xg_range")
    st.sidebar.slider("PPDA", 18.0, 0.0, (18.0, 0.0), -1.0, key="ppda_range")
    st.sidebar.slider("Counter Attacking Shots", 0.0, 3.0, (0.0, 3.0), 0.1, key="counter_shots_range")
    st.sidebar.slider("Open Play Shot Distance", 30.0, 10.0, (30.0, 10.0), -1.0, key="shot_distance_range")
    st.sidebar.slider("Open Play Shot Distance Conceded", 10.0, 30.0, (10.0, 30.0), 1.0, key="shot_distance_conceded_range")
    st.sidebar.slider("Pressures in opposition half Ratio", 0.0, 1.0, (0.0, 1.0), 0.05, key="fhalf_pressure_range")
    st.sidebar.slider("Possession Ratio", 0.0, 1.0, (0.0, 1.0), 0.05, key="possession_range")
    st.sidebar.slider("xG Conceded", 3.0, 0.0, (3.0, 0.0), -0.1, key="xg_conceded_range")

    if st.sidebar.button("Load Data") or st.session_state.data_loaded:
        if not st.session_state.data_loaded:
            try:
                selected_comp_ids = {k: v for k, v in COMPETITIONS.items() if v in selected_competitions}
                selected_season_ids = {k: v for k, v in SEASONS.items() if v in selected_seasons}

                manager_data, matches = fetch_manager_data(email, password, selected_comp_ids, selected_season_ids)
                team_stats = fetch_team_stats(email, password, matches, manager_data)

                st.info("Merging and cleaning data...")
                merged_data = pd.merge(manager_data, team_stats, on=["team_name", "manager", "competition", "season"], how="left")
                cleaned_data = merged_data[["team_name", "manager", "games_managed", "competition", "season"] + list(METRICS.keys())]
                cleaned_data.rename(columns=METRICS, inplace=True)

                cleaned_data = cleaned_data[cleaned_data["games_managed"] >= st.session_state.min_matches]

                st.session_state.manager_data = manager_data
                st.session_state.matches = matches
                st.session_state.team_stats = team_stats
                st.session_state.cleaned_data = cleaned_data
                st.session_state.data_loaded = True
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

        # Use data from session state
        cleaned_data = st.session_state.cleaned_data

        # Remove rows where the 'manager' column is empty or NaN
        cleaned_data = cleaned_data[cleaned_data['manager'].notnull() & (cleaned_data['manager'] != "")]

        # Remove duplicate rows where the same manager is managing the same team
        cleaned_data = cleaned_data.drop_duplicates(subset=["manager", "team_name", "competition"])

        # Drop the 'season' column
        cleaned_data = cleaned_data.drop(columns=["season"])

        st.write("### Merged Data for Selected Competitions and Seasons")
        st.dataframe(cleaned_data)

        # Apply filtering logic based on slider values
        filtered_data = cleaned_data[
            (cleaned_data["games_managed"] >= st.session_state.min_matches) &
            (cleaned_data["Open Play xG"].between(*st.session_state.op_xg_range)) &
            (cleaned_data["Set Piece xG"].between (*st.session_state.sp_xg_range)) &
            (cleaned_data["PPDA"].between (*st.session_state.ppda_range)) &
            (cleaned_data["Counter Attacking Shots"].between (*st.session_state.counter_shots_range)) &
            (cleaned_data["Open Play Shot Distance"].between (*st.session_state.shot_distance_range)) &
            (cleaned_data["Open Play Shot Distance Conceded"].between (*st.session_state.shot_distance_conceded_range)) &
            (cleaned_data["Pressures in opposition half Ratio"].between (*st.session_state.fhalf_pressure_range)) &
            (cleaned_data["Possession Ratio"].between (*st.session_state.possession_range)) &
            (cleaned_data["xG Conceded"].between (*st.session_state.xg_conceded_range))
        ]

        if filtered_data.empty:
            st.warning("No managers meet the selected criteria. Adjust your filters and try again.")
        else:
            st.write("### Selected Managers")
            st.dataframe(filtered_data)


            # Normalize games managed for the color mapping
            norm = mcolors.Normalize(vmin=filtered_data["games_managed"].min(), vmax=filtered_data["games_managed"].max())
            cmap = cm.get_cmap("Reds")  # Choose a colormap or define a custom one
            
            # Define your custom gradient colors
            custom_cmap = mcolors.LinearSegmentedColormap.from_list("", ["#fcb9b2", "#461220"])
            
            # Map the number of games managed to colors
            colors = filtered_data["games_managed"].apply(lambda x: custom_cmap(norm(x)))

            st.write("### Comparison")
            for metric, label in METRICS.items():
                if label in filtered_data.columns:  # Ensure the column exists in the filtered data
                    fig, ax = plt.subplots(figsize=(8, 6))
            
                    # Normalize the metric column for consistent color mapping
                    norm = mcolors.Normalize(vmin=filtered_data[label].min(), vmax=filtered_data[label].max())
                    color_list = [custom_cmap(norm(value)) for value in filtered_data[label]]  # Generate color list
            
                    # Plot using the color list
                    sns.barplot(
                        data=filtered_data,
                        x=label,  # Use the mapped column name for the x-axis
                        y="manager",
                        palette=color_list,  # Pass the list of colors directly
                        ax=ax
                    )
            
                    # Set chart title and labels
                    ax.set_title(f"{label}")
                    ax.set_xlabel("")  # Remove x-axis label
                    ax.set_ylabel("Managers")
                    st.pyplot(fig)
                else:
                    st.warning(f"Column '{label}' is missing in the data.")
