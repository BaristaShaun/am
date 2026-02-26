import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import tempfile
import os
import re

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

    tab1, tab2, tab3, tab4 = st.tabs(["Lifecycle Breakdown", "Scenario by Location", "Multi-Country Comparison", "PDF Report Generator"])

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

    with tab4:
        st.subheader("📄 LCA Report - Baseline vs AM Scenario")
        st.markdown("### Generate a comprehensive GWP comparison report in PDF format")
        st.markdown("---")
        
        # 1. Executive Summary
        st.header("1. Executive Summary")
        exec_summary = st.text_area(
            "Summary Content (English)",
            value="**Purpose:** Compare GWP between Baseline product and AM (Additive Manufacturing) scenario\n"
                  "**Key Results:** Country-specific GWP reduction rates\n"
                  "**Representative Graphic:** World map showing country-level GWP reduction via Bar Chart",
            height=120,
            key="exec_summary"
        )
        
        # 2. Methodology
        st.header("2. Methodology")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            functional_unit = st.text_input("Functional Unit", value="1 unit of SGT-500 Gas Turbine Blade", key="func_unit")
            method = st.selectbox("Assessment Method", ["Gate-to-Gate", "Cradle-to-Gate", "Cradle-to-Grave"], key="method")
        with col_m2:
            assessment_tool = st.text_input("Assessment Tool", value="OpenLCA / Python-based LCA", key="tool")
            data_source = st.text_input("Data Source", value="Ecoinvent 3.8, Country-specific grid mix", key="data_source")
        
        data_quality = st.text_area(
            "Data Quality & Assumptions",
            value="• Data sources: Country-specific energy emission factors, process data from manufacturing sites\n"
                  "• Assumptions: Standard transportation routes, average downtime periods, material efficiency rates\n"
                  "• Data quality: Primary data for energy and material use, secondary data for emission factors",
            height=100,
            key="data_quality"
        )
        
        # 3. Results - Multi-Country GWP Comparison
        st.header("3. Results - GWP Comparison")
        st.markdown("**Baseline vs AM Scenario GWP by Country**")
        st.info("📌 The data below is automatically calculated based on your input parameters from Page 1")
        
        # Calculate for all countries
        results_data = {
            'Country': [],
            'Baseline (kg CO2e)': [],
            'AM Scenario (kg CO2e)': [],
            'Reduction (%)': []
        }
        
        for country, grid_val in grid_mix_dict.items():
            # Standard (Baseline) calculation
            manuf_std_c = manufacturing_co2(defaults_num["energy_standard"], grid_val)
            downtime_std_c = downtime_co2(defaults_num["turbine_output"], defaults_num["efficiency_loss"], hours_std, grid_val)
            total_std_c = mat_std + manuf_std_c + transport_std + downtime_std_c
            
            # AM Scenario calculation
            manuf_am_c = manufacturing_co2(defaults_num["energy_am"], grid_val, defaults_num["argon_use_am"], defaults_num["argon_emission_factor"])
            downtime_am_c = downtime_co2(defaults_num["turbine_output"], defaults_num["efficiency_loss"], hours_am, grid_val)
            total_am_c = mat_am + manuf_am_c + transport_am + downtime_am_c
            
            # Calculate reduction
            reduction_pct = ((total_std_c - total_am_c) / total_std_c * 100) if total_std_c > 0 else 0
            
            results_data['Country'].append(country)
            results_data['Baseline (kg CO2e)'].append(round(total_std_c, 2))
            results_data['AM Scenario (kg CO2e)'].append(round(total_am_c, 2))
            results_data['Reduction (%)'].append(round(reduction_pct, 1))
        
        results_df = pd.DataFrame(results_data)
        
        st.dataframe(results_df.style.format({
            'Baseline (kg CO2e)': '{:.2f}',
            'AM Scenario (kg CO2e)': '{:.2f}',
            'Reduction (%)': '{:.1f}%'
        }).background_gradient(subset=['Reduction (%)'], cmap='Greens'), use_container_width=True)
        
        # Allow user to edit results if needed
        st.markdown("**Optional: Edit results manually for the report**")
        edited_results = st.data_editor(results_df, num_rows="dynamic", use_container_width=True, key="edited_results")
        
        # 4. Visualization Preview
        st.header("4. Visualization Preview")
        st.markdown("The following charts will be included in the PDF report:")
        
        col_v1, col_v2 = st.columns(2)
        
        with col_v1:
            st.subheader("Bar Chart: Baseline vs AM Scenario")
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                name='Baseline',
                x=edited_results['Country'],
                y=edited_results['Baseline (kg CO2e)'],
                marker_color='#5b2c6f',
                text=edited_results['Baseline (kg CO2e)'].round(1),
                textposition='outside'
            ))
            fig_bar.add_trace(go.Bar(
                name='AM Scenario',
                x=edited_results['Country'],
                y=edited_results['AM Scenario (kg CO2e)'],
                marker_color='#008b8b',
                text=edited_results['AM Scenario (kg CO2e)'].round(1),
                textposition='outside'
            ))
            fig_bar.update_layout(
                barmode='group',
                xaxis_title='Country',
                yaxis_title='GWP (kg CO₂e)',
                height=400,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col_v2:
            st.subheader("Dual-line Chart")
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=edited_results['Country'],
                y=edited_results['Baseline (kg CO2e)'],
                mode='lines+markers',
                name='Baseline',
                line=dict(color='#5b2c6f', width=3),
                marker=dict(size=10)
            ))
            fig_line.add_trace(go.Scatter(
                x=edited_results['Country'],
                y=edited_results['AM Scenario (kg CO2e)'],
                mode='lines+markers',
                name='AM Scenario',
                line=dict(color='#008b8b', width=3),
                marker=dict(size=10)
            ))
            fig_line.update_layout(
                xaxis_title='Country',
                yaxis_title='GWP (kg CO₂e)',
                height=400,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_line, use_container_width=True)
        
        # Reduction percentage bar chart
        st.subheader("Reduction Rate by Country")
        fig_reduction = go.Figure()
        fig_reduction.add_trace(go.Bar(
            x=edited_results['Country'],
            y=edited_results['Reduction (%)'],
            marker_color='#2ecc71',
            text=edited_results['Reduction (%)'].round(1),
            texttemplate='%{text}%',
            textposition='outside'
        ))
        fig_reduction.update_layout(
            xaxis_title='Country',
            yaxis_title='Reduction (%)',
            height=350,
            showlegend=False
        )
        st.plotly_chart(fig_reduction, use_container_width=True)
        
        # World Map
        st.subheader("Geographic Distribution of GWP Reduction")
        fig_map = go.Figure(data=go.Choropleth(
            locations=edited_results['Country'],
            locationmode='country names',
            z=edited_results['Reduction (%)'],
            text=edited_results['Country'],
            colorscale='Greens',
            colorbar_title='Reduction %',
            marker_line_color='darkgray',
            marker_line_width=0.5,
        ))
        fig_map.update_layout(
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type='natural earth'
            ),
            height=400
        )
        st.plotly_chart(fig_map, use_container_width=True)
        
        # 5. Interpretation
        st.header("5. Interpretation")
        interpretation = st.text_area(
            "Key Findings & Analysis (English)",
            value="• AM technology demonstrates GWP reduction benefits across all analyzed countries\n"
                  "• Reduction rates vary by country due to differences in energy mix and manufacturing process efficiency\n"
                  "• Countries with higher carbon-intensive grid mix show greater absolute GWP savings\n"
                  "• Material efficiency improvements (less waste) contribute significantly to overall reduction\n"
                  "• Reduced transportation distances in AM scenarios provide additional environmental benefits",
            height=150,
            key="interpretation"
        )
        
        # 6. Conclusion
        st.header("6. Conclusion")
        conclusion = st.text_area(
            "Conclusion (English)",
            value="• GWP reduction through AM adoption shows positive environmental impact\n"
                  "• Country-specific strategies are necessary considering different energy mix profiles\n"
                  "• AM technology offers substantial benefits in material efficiency and supply chain optimization\n"
                  "• Continued monitoring and optimization of AM processes recommended for maximum GWP reduction",
            height=120,
            key="conclusion"
        )
        
        # Additional notes
        st.header("7. Additional Information (Optional)")
        col_add1, col_add2 = st.columns(2)
        with col_add1:
            report_author = st.text_input("Report Author", value="LCA Engineering Team", key="author")
            organization = st.text_input("Organization", value="Siemens Energy", key="org")
        with col_add2:
            project_name = st.text_input("Project Name", value="Gas Turbine Blade LCA Study", key="project")
            report_version = st.text_input("Report Version", value="v1.0", key="version")
        
        # PDF Generation Function
        def format_text_for_pdf(text):
            """Convert markdown-style bold (**text**) to HTML bold tags and escape HTML entities"""
            # Escape HTML special characters first
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            # Replace **text** with <b>text</b>
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            return text
        
        def escape_html(text):
            """Escape HTML special characters"""
            text = str(text)
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            return text
        
        def create_lca_pdf_report(data_df, exec_sum, func_unit, assess_method, tool, data_src, 
                                 data_qual, interpret, concl, author, org, project, version,
                                 fig_bar, fig_line, fig_reduction, fig_map):
            """Generate comprehensive LCA PDF report"""
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                   rightMargin=50, leftMargin=50, 
                                   topMargin=50, bottomMargin=30)
            
            story = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'ReportTitle',
                parent=styles['Heading1'],
                fontSize=22,
                textColor=colors.HexColor('#5b2c6f'),
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            heading1_style = ParagraphStyle(
                'CustomHeading1',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#5b2c6f'),
                spaceAfter=12,
                spaceBefore=12,
                fontName='Helvetica-Bold'
            )
            
            heading2_style = ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontSize=13,
                textColor=colors.HexColor('#008b8b'),
                spaceAfter=8,
                spaceBefore=8,
                fontName='Helvetica-Bold'
            )
            
            # Report Title
            story.append(Paragraph("LCA Report", title_style))
            story.append(Paragraph("Baseline vs AM Scenario - GWP Comparison", heading2_style))
            story.append(Spacer(1, 15))
            
            # Report metadata
            metadata = f"""
            <b>Project:</b> {escape_html(project)}<br/>
            <b>Organization:</b> {escape_html(org)}<br/>
            <b>Author:</b> {escape_html(author)}<br/>
            <b>Version:</b> {escape_html(version)}<br/>
            <b>Date:</b> {datetime.now().strftime('%B %d, %Y')}
            """
            story.append(Paragraph(metadata, styles['Normal']))
            story.append(Spacer(1, 30))
            story.append(PageBreak())
            
            # 1. Executive Summary
            story.append(Paragraph("1. Executive Summary", heading1_style))
            story.append(Spacer(1, 10))
            for line in exec_sum.split('\n'):
                if line.strip():
                    formatted_line = format_text_for_pdf(line)
                    story.append(Paragraph(formatted_line, styles['Normal']))
                    story.append(Spacer(1, 8))
            story.append(Spacer(1, 20))
            
            # 2. Methodology
            story.append(Paragraph("2. Methodology", heading1_style))
            story.append(Spacer(1, 10))
            
            methodology_content = f"""
            <b>Functional Unit:</b> {escape_html(func_unit)}<br/>
            <b>Assessment Method:</b> {escape_html(assess_method)}<br/>
            <b>Assessment Tool:</b> {escape_html(tool)}<br/>
            <b>Data Source:</b> {escape_html(data_src)}<br/>
            """
            story.append(Paragraph(methodology_content, styles['Normal']))
            story.append(Spacer(1, 12))
            
            story.append(Paragraph("<b>Data Quality & Assumptions:</b>", styles['Normal']))
            story.append(Spacer(1, 8))
            for line in data_qual.split('\n'):
                if line.strip():
                    formatted_line = format_text_for_pdf(line)
                    story.append(Paragraph(formatted_line, styles['Normal']))
                    story.append(Spacer(1, 6))
            
            story.append(PageBreak())
            
            # 3. Results
            story.append(Paragraph("3. Results - GWP Comparison", heading1_style))
            story.append(Spacer(1, 10))
            story.append(Paragraph("Country-level Baseline vs AM Scenario GWP:", heading2_style))
            story.append(Spacer(1, 12))
            
            # Results table
            table_data = [['Country', 'Baseline\n(kg CO₂e)', 'AM Scenario\n(kg CO₂e)', 'Reduction\n(%)']]
            for _, row in data_df.iterrows():
                table_data.append([
                    row['Country'],
                    f"{row['Baseline (kg CO2e)']:.2f}",
                    f"{row['AM Scenario (kg CO2e)']:.2f}",
                    f"{row['Reduction (%)']}%"
                ])
            
            # Add statistics row
            avg_baseline = data_df['Baseline (kg CO2e)'].mean()
            avg_am = data_df['AM Scenario (kg CO2e)'].mean()
            avg_reduction = data_df['Reduction (%)'].mean()
            table_data.append(['Average', f"{avg_baseline:.2f}", f"{avg_am:.2f}", f"{avg_reduction:.1f}%"])
            
            results_table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.2*inch])
            results_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5b2c6f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f5f5f5')),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9f9f9')])
            ]))
            story.append(results_table)
            story.append(PageBreak())
            
            # 4. Visualization
            story.append(Paragraph("4. Visualization", heading1_style))
            story.append(Spacer(1, 15))
            
            # Save charts as temporary images
            temp_files = []
            
            try:
                # Bar Chart
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp1:
                    fig_bar.write_image(tmp1.name, width=900, height=500, scale=2)
                    temp_files.append(tmp1.name)
                    story.append(Paragraph("Bar Chart: Country-level Baseline vs AM Scenario GWP", heading2_style))
                    story.append(Spacer(1, 8))
                    img1 = Image(tmp1.name, width=6*inch, height=3.3*inch)
                    story.append(img1)
                    story.append(Spacer(1, 20))
                
                # Line Chart
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp2:
                    fig_line.write_image(tmp2.name, width=900, height=500, scale=2)
                    temp_files.append(tmp2.name)
                    story.append(Paragraph("Dual-line Chart: Trend Comparison (Baseline vs AM)", heading2_style))
                    story.append(Spacer(1, 8))
                    img2 = Image(tmp2.name, width=6*inch, height=3.3*inch)
                    story.append(img2)
                
                story.append(PageBreak())
                
                # Reduction Chart
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp3:
                    fig_reduction.write_image(tmp3.name, width=900, height=450, scale=2)
                    temp_files.append(tmp3.name)
                    story.append(Paragraph("GWP Reduction Rate by Country", heading2_style))
                    story.append(Spacer(1, 8))
                    img3 = Image(tmp3.name, width=6*inch, height=3*inch)
                    story.append(img3)
                    story.append(Spacer(1, 20))
                
                # World Map
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp4:
                    fig_map.write_image(tmp4.name, width=900, height=500, scale=2)
                    temp_files.append(tmp4.name)
                    story.append(Paragraph("Geographic Distribution: Reduction Map (World View)", heading2_style))
                    story.append(Spacer(1, 8))
                    img4 = Image(tmp4.name, width=6*inch, height=3.3*inch)
                    story.append(img4)
                
                story.append(PageBreak())
                
                # 5. Interpretation
                story.append(Paragraph("5. Interpretation", heading1_style))
                story.append(Spacer(1, 10))
                for line in interpret.split('\n'):
                    if line.strip():
                        formatted_line = format_text_for_pdf(line)
                        story.append(Paragraph(formatted_line, styles['Normal']))
                        story.append(Spacer(1, 8))
                story.append(Spacer(1, 20))
                
                # 6. Conclusion
                story.append(Paragraph("6. Conclusion", heading1_style))
                story.append(Spacer(1, 10))
                for line in concl.split('\n'):
                    if line.strip():
                        formatted_line = format_text_for_pdf(line)
                        story.append(Paragraph(formatted_line, styles['Normal']))
                        story.append(Spacer(1, 8))
                
                # Build PDF
                doc.build(story)
                buffer.seek(0)
                
                return buffer, temp_files
                
            except Exception as e:
                raise Exception(f"Error creating PDF: {str(e)}")
        
        # Generate PDF Button
        st.markdown("---")
        st.header("8. Generate PDF Report")
        
        if st.button("🎯 Generate PDF Report", type="primary", key="generate_pdf"):
            if not edited_results.empty:
                try:
                    with st.spinner("Generating comprehensive PDF report... This may take a moment."):
                        pdf_buffer, temp_files = create_lca_pdf_report(
                            edited_results, 
                            exec_summary,
                            functional_unit,
                            method,
                            assessment_tool,
                            data_source,
                            data_quality,
                            interpretation,
                            conclusion,
                            report_author,
                            organization,
                            project_name,
                            report_version,
                            fig_bar,
                            fig_line,
                            fig_reduction,
                            fig_map
                        )
                    
                    st.success("✅ PDF Report Generated Successfully!")
                    
                    filename = f"LCA_Report_Baseline_vs_AM_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_buffer,
                        file_name=filename,
                        mime="application/pdf",
                        key="download_pdf"
                    )
                    
                    # Clean up temporary files
                    for tmp_file in temp_files:
                        try:
                            if os.path.exists(tmp_file):
                                os.remove(tmp_file)
                        except:
                            pass
                    
                    st.info("💡 The PDF includes all sections with visualizations and detailed analysis.")
                    
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {str(e)}")
                    st.info("**Troubleshooting:** Make sure `kaleido` package is installed:\n```\npip install kaleido\n```")
            else:
                st.warning("⚠ Please ensure results data is available before generating the report.")
