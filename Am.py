import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- DEFAULTS ---
defaults_str = {
    "material_type": "Ni-based Alloy"
}

defaults_num = {
    "raw_weight": 4.0,  # kg
    "finished_weight": 3.2,  # kg
    "material_emission": 22.0,  # kg CO2e/kg
    "energy_standard": 150.0,  # kWh
    "energy_am": 90.0,  # kWh
    "argon_use_am": 2.0,  # m3
    "argon_emission_factor": 0.5,  # kg CO2e/m3
    "transport_standard_km": 9000.0,  # km
    "transport_am_km": 500.0,  # km
    "transport_factor_air": 0.6,  # kg CO2e/t.km
    "downtime_standard_months": 6.0,  # months
    "downtime_am_weeks": 2.0,  # weeks
    "efficiency_loss": 0.02,  # fraction
    "turbine_output": 50.0,  # MW
    "grid_germany": 0.4,  # kg CO2e/kWh
}

grid_mix_dict = {
    "Germany": 0.4,
    "USA": 0.25,
    "China": 0.75,
    "Japan": 0.43,
    "France": 0.07,
    "UK": 0.27,
    "India": 0.71,
    "Brazil": 0.08,
    "Australia": 0.58,
    "Canada": 0.16
}

# --- PAGE SELECTION ---
pages = ["Page 1: Input Data", "Page 2: Results"]
page = st.sidebar.selectbox("Select Page", pages)

# --- Functions ---
def material_co2(raw_weight, factor):
    return raw_weight * factor

def manufacturing_co2(energy_kwh, grid_mix, gas=0, gas_factor=0):
    return (energy_kwh * grid_mix) + (gas * gas_factor)

def transport_co2(weight_tons, km, factor):
    return weight_tons * km * factor

def downtime_co2(output_mw, loss_rate, hours, grid_mix):
    return (output_mw * loss_rate * hours) * grid_mix

# --- PAGE 1 ---
if page == pages[0]:
    st.title("Production Site Input Requirements - Blade Case")

    st.subheader("Material Information")
    defaults_str["material_type"] = st.text_input("Material Type", defaults_str["material_type"])
    st.caption("Type of alloy used for blades (example: Ni-based alloy). Determines material emission factor.")

    for key, val in defaults_num.items():
        units = {
            "raw_weight": "kg",
            "finished_weight": "kg",
            "material_emission": "kg CO₂e/kg",
            "energy_standard": "kWh",
            "energy_am": "kWh",
            "argon_use_am": "m³",
            "argon_emission_factor": "kg CO₂e/m³",
            "transport_standard_km": "km",
            "transport_am_km": "km",
            "transport_factor_air": "kg CO₂e/t·km",
            "downtime_standard_months": "months",
            "downtime_am_weeks": "weeks",
            "efficiency_loss": "",
            "turbine_output": "MW",
            "grid_germany": "kg CO₂e/kWh"
        }
        defaults_num[key] = st.number_input(
            f"{key.replace('_',' ').title()} ({units[key]})",
            value=val
        )
        explanations = {
            "raw_weight": "Weight of semi-finished raw material before machining.",
            "finished_weight": "Final weight of the blade after manufacturing.",
            "material_emission": "Emission factor for the chosen alloy material.",
            "energy_standard": "Manufacturing energy consumption for standard process.",
            "energy_am": "Manufacturing energy consumption for AM process.",
            "argon_use_am": "Volume of shielding gas used in AM process.",
            "argon_emission_factor": "Emission factor of shielding gas.",
            "transport_standard_km": "Transport distance for standard manufacturing route.",
            "transport_am_km": "Transport distance for AM manufacturing route (usually local).",
            "transport_factor_air": "Emission factor for air transport per ton·km.",
            "downtime_standard_months": "Downtime duration with standard process.",
            "downtime_am_weeks": "Downtime duration with AM process.",
            "efficiency_loss": "Efficiency loss rate during downtime.",
            "turbine_output": "Output power of the turbine.",
            "grid_germany": "Grid mix emission factor for Germany."
        }
        st.caption(explanations.get(key, ""))

# --- PAGE 2 ---
elif page == pages[1]:
    st.title("Blade Case - LCA Results")

    weight_tons_std = defaults_num["finished_weight"] / 1000
    weight_tons_am = defaults_num["finished_weight"] / 1000

    hours_std = defaults_num["downtime_standard_months"] * 30 * 24
    hours_am = defaults_num["downtime_am_weeks"] * 7 * 24

    # Germany baseline calculations
    mat_std = material_co2(defaults_num["raw_weight"], defaults_num["material_emission"])
    mat_am  = material_co2(defaults_num["finished_weight"], defaults_num["material_emission"])

    manuf_std = manufacturing_co2(defaults_num["energy_standard"], defaults_num["grid_germany"])
    manuf_am  = manufacturing_co2(defaults_num["energy_am"], defaults_num["grid_germany"], defaults_num["argon_use_am"], defaults_num["argon_emission_factor"])

    transport_std = transport_co2(weight_tons_std, defaults_num["transport_standard_km"], defaults_num["transport_factor_air"])
    transport_am  = transport_co2(weight_tons_am, defaults_num["transport_am_km"], defaults_num["transport_factor_air"])

    downtime_std = downtime_co2(defaults_num["turbine_output"], defaults_num["efficiency_loss"], hours_std, defaults_num["grid_germany"])
    downtime_am  = downtime_co2(defaults_num["turbine_output"], defaults_num["efficiency_loss"], hours_am, defaults_num["grid_germany"])

    df = pd.DataFrame({
        "Stage": ["Material", "Manufacturing", "Transport", "Downtime"],
        "Standard": [mat_std, manuf_std, transport_std, downtime_std],
        "AM": [mat_am, manuf_am, transport_am, downtime_am]
    })

    tab1, tab2, tab3 = st.tabs(["Lifecycle Breakdown", "Scenario by Location", "Multi-Country Comparison"])

    with tab1:
        st.subheader("Lifecycle Stage Emissions (Germany Grid Mix)")
        st.caption("""
        **Material**: CO₂ from raw material production  
        **Manufacturing**: CO₂ from energy use during manufacturing & protective gas in AM  
        **Transport**: CO₂ from moving finished/semi-finished parts to site  
        **Downtime**: CO₂ from efficiency loss during repair period
        """)
        total_std = df["Standard"].sum()
        total_am = df["AM"].sum()
        st.metric("CO₂ Reduction (%)", round(((total_std-total_am)/total_std)*100, 2))
        fig = go.Figure(data=[
            go.Bar(name='Standard', x=df["Stage"], y=df["Standard"], text=df["Standard"], textposition='auto'),
            go.Bar(name='AM', x=df["Stage"], y=df["AM"], text=df["AM"], textposition='auto')
        ])
        fig.update_layout(barmode='group', yaxis_title="kg CO₂e")
        st.plotly_chart(fig)

    with tab2:
        st.subheader("Scenario by Production Location")
        country_select = st.selectbox("Select production location", list(grid_mix_dict.keys()), index=0)
        grid_val = grid_mix_dict[country_select]

        manuf_std_c = manufacturing_co2(defaults_num["energy_standard"], grid_val)
        manuf_am_c  = manufacturing_co2(defaults_num["energy_am"], grid_val, defaults_num["argon_use_am"], defaults_num["argon_emission_factor"])
        downtime_std_c = downtime_co2(defaults_num["turbine_output"], defaults_num["efficiency_loss"], hours_std, grid_val)
        downtime_am_c  = downtime_co2(defaults_num["turbine_output"], defaults_num["efficiency_loss"], hours_am, grid_val)

        df_country = pd.DataFrame({
            "Stage": ["Material", "Manufacturing", "Transport", "Downtime"],
            "Standard": [mat_std, manuf_std_c, transport_std, downtime_std_c],
            "AM": [mat_am, manuf_am_c, transport_am, downtime_am_c]
        })
        
        # Create comparison table
        df_comparison = df_country.copy()
        df_comparison["Difference (Standard - AM)"] = df_comparison["Standard"] - df_comparison["AM"]
        df_comparison["% Reduction"] = ((df_comparison["Standard"] - df_comparison["AM"]) / df_comparison["Standard"] * 100).round(2)
        
        # Add total row
        total_std_c = df_comparison["Standard"].sum()
        total_am_c = df_comparison["AM"].sum()
        total_diff = total_std_c - total_am_c
        total_reduction = ((total_std_c - total_am_c) / total_std_c * 100)
        
        df_total = pd.DataFrame({
            "Stage": ["Total"],
            "Standard": [total_std_c],
            "AM": [total_am_c],
            "Difference (Standard - AM)": [total_diff],
            "% Reduction": [total_reduction]
        })
        
        df_comparison = pd.concat([df_comparison, df_total], ignore_index=True)
        
        st.dataframe(df_comparison.style.format({
            "Standard": "{:.2f}",
            "AM": "{:.2f}",
            "Difference (Standard - AM)": "{:.2f}",
            "% Reduction": "{:.2f}%"
        }).highlight_max(subset=["% Reduction"], color='lightgreen'))
        
        st.metric("Total CO₂ Reduction", f"{total_diff:.2f} kg CO₂e", f"{total_reduction:.2f}%")
        
        fig3 = go.Figure(data=[
            go.Bar(name='Standard', x=df_country["Stage"], y=df_country["Standard"], text=df_country["Standard"], textposition='auto'),
            go.Bar(name='AM', x=df_country["Stage"], y=df_country["AM"], text=df_country["AM"], textposition='auto')
        ])
        fig3.update_layout(barmode='group', yaxis_title="kg CO₂e", title=f"Comparison for {country_select}")
        st.plotly_chart(fig3)

    with tab3:
        st.subheader("Multi-Country Comparison")
        st.caption("Select countries to compare total emissions by lifecycle stage")
        
        # Create checkboxes for country selection
        st.write("**Select Countries:**")
        cols = st.columns(5)
        selected_countries = []
        
        countries_list = list(grid_mix_dict.keys())
        for idx, country in enumerate(countries_list):
            with cols[idx % 5]:
                if st.checkbox(country, value=(idx < 3), key=f"country_{country}"):
                    selected_countries.append(country)
        
        if len(selected_countries) == 0:
            st.warning("Please select at least one country to compare.")
        else:
            # Calculate emissions for each selected country
            comparison_data = {
                "Country": [],
                "Material": [],
                "Manufacturing": [],
                "Transport": [],
                "Downtime": [],
                "Total": []
            }
            
            for country in selected_countries:
                grid_val = grid_mix_dict[country]
                
                # Calculate lifecycle stages
                manuf_c = manufacturing_co2(defaults_num["energy_standard"], grid_val)
                downtime_c = downtime_co2(defaults_num["turbine_output"], defaults_num["efficiency_loss"], hours_std, grid_val)
                
                comparison_data["Country"].append(country)
                comparison_data["Material"].append(mat_std)
                comparison_data["Manufacturing"].append(manuf_c)
                comparison_data["Transport"].append(transport_std)
                comparison_data["Downtime"].append(downtime_c)
                comparison_data["Total"].append(mat_std + manuf_c + transport_std + downtime_c)
            
            df_multi = pd.DataFrame(comparison_data)
            
            # Display summary table
            st.dataframe(df_multi.style.format({
                "Material": "{:.2f}",
                "Manufacturing": "{:.2f}",
                "Transport": "{:.2f}",
                "Downtime": "{:.2f}",
                "Total": "{:.2f}"
            }).highlight_max(subset=["Total"], color='lightcoral').highlight_min(subset=["Total"], color='lightgreen'))
            
            # Create stacked bar chart
            fig_multi = go.Figure()
            
            fig_multi.add_trace(go.Bar(
                name='Material',
                x=df_multi["Country"],
                y=df_multi["Material"],
                text=df_multi["Material"].round(2),
                textposition='inside'
            ))
            
            fig_multi.add_trace(go.Bar(
                name='Manufacturing',
                x=df_multi["Country"],
                y=df_multi["Manufacturing"],
                text=df_multi["Manufacturing"].round(2),
                textposition='inside'
            ))
            
            fig_multi.add_trace(go.Bar(
                name='Transport',
                x=df_multi["Country"],
                y=df_multi["Transport"],
                text=df_multi["Transport"].round(2),
                textposition='inside'
            ))
            
            fig_multi.add_trace(go.Bar(
                name='Downtime',
                x=df_multi["Country"],
                y=df_multi["Downtime"],
                text=df_multi["Downtime"].round(2),
                textposition='inside'
            ))
            
            fig_multi.update_layout(
                barmode='stack',
                yaxis_title="kg CO₂e",
                title="Stacked Lifecycle Emissions by Country (Standard Process)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig_multi, use_container_width=True)
