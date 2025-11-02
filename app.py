import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json
import gtts
from fpdf import FPDF
import tempfile
import os
import importlib.util
import matplotlib.pyplot as plt
import numpy as np
from smart_summary import get_Summary
from prompt import full_prompt

# Page setup
st.set_page_config(page_title="Insight Agent", page_icon="🤖", layout="wide")

# Basic CSS
st.markdown("""
<style>
.stApp { background-color: #f1f5f2; }
h1 { color: #1b263b; text-align: center; font-weight: 800; }
div[data-testid="stFileUploader"] {
    background-color: #d9e4dd;
    border: 2px dashed #2a9d8f;
    padding: 1em;
    border-radius: 10px;
}
div.stButton > button:first-child {
    background: linear-gradient(90deg, #264653, #2a9d8f);
    color: white; font-weight: 600; border-radius: 8px;
}
div.stButton > button:first-child:hover {
    background: linear-gradient(90deg, #2a9d8f, #264653);
}
</style>
""", unsafe_allow_html=True)

# API config
API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-pro")

# Header
st.title("INSIGHT AGENT 🤖📊")
st.header("Turn your Data into a Story")

# File upload
data = st.file_uploader("Upload your dataset (Max 4000 rows)", type=["csv", "xls", "xlsx"])

if data is not None:
    if data.name.endswith(".csv"):
        df = pd.read_csv(data)
    else:
        df = pd.read_excel(data)

    if df.shape[0] <= 4000:
        st.success("✅ File uploaded successfully!")
        st.dataframe(df.head(5), use_container_width=True)

        smart_summary = get_Summary(df)

        role = st.pills("Select your Role", ["CEO", "Investor", "Sales Manager", "Employee", "Teacher", "Student", "Patient", "Doctor"])
        tone = st.pills("Select your Tone", ["Formal", "Casual", "Conversational", "Friendly", "Professional"])

        if st.button("📊 Analyze Your Data", use_container_width=True):
            with st.spinner("Agent is analyzing your data..."):
                prompt = full_prompt(tone, role, smart_summary)
                response = model.generate_content(prompt)
                clean_response = response.text.strip('```json\n').strip('\n```')
                st.toast('✨ Analysis Finished!')

                agent_report = json.loads(clean_response)
                executive_summary = agent_report["executive_summary"]
                key_insights = agent_report["key_insights"]
                data_quality = agent_report["data_quality_issues"]
                recommendations = agent_report["recommendations"]
                chart_codes = agent_report["plot_codes"]
                reg = agent_report["regression_suggestion"]

            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
                ["Smart Summary", "Key Insights", "Data Quality", "Recommendations", "Charts", "Regression"]
            )

            with tab1:
                st.info(executive_summary)
                tts = gtts.gTTS(text=executive_summary, lang='en')
                tts.save("report.mp3")
                st.audio("report.mp3", autoplay=True)

            with tab2:
                for text in key_insights:
                    st.write(text)

            with tab3:
                for text in data_quality:
                    st.write(text)

            with tab4:
                for text in recommendations:
                    st.write(text)

            # Interactive charts in app
            with tab5:
                try:
                    scope_dict = {"df": df, "px": px}
                    for code in chart_codes:
                        exec(code, scope_dict)
                        fig = scope_dict["fig"]
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error in chart generation: {e}")

            # Regression chart in app
            with tab6:
                try:
                    target_col = reg['target_variable']
                    feature_col = reg['feature_variable']
                    has_statsmodels = importlib.util.find_spec("statsmodels") is not None
                    if has_statsmodels:
                        reg_fig = px.scatter(df, x=feature_col, y=target_col,
                                             trendline='ols', trendline_color_override='red')
                    else:
                        reg_fig = px.scatter(df, x=feature_col, y=target_col)
                        reg_fig.update_traces(marker=dict(color='blue'))
                        reg_fig.add_annotation(
                            text="OLS disabled (statsmodels missing)",
                            xref="paper", yref="paper", showarrow=False, yshift=20
                        )
                    st.plotly_chart(reg_fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Regression plot error: {e}")

            # Generate PDF
            try:
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.set_margins(15, 15, 15)
                pdf.add_page()

                base_path = os.path.join(os.getcwd(), "dejavu-fonts-ttf-2.37", "ttf")
                font_path_regular = os.path.join(base_path, "DejaVuSans.ttf")
                font_path_bold = os.path.join(base_path, "DejaVuSans-Bold.ttf")

                pdf.add_font("DejaVu", "", font_path_regular, uni=True)
                pdf.add_font("DejaVu", "B", font_path_bold, uni=True)
                pdf.set_font("DejaVu", "B", 20)
                pdf.cell(0, 10, "InsightAgent AI Report", ln=True, align='C')
                pdf.ln(10)

                def write_section(title, content):
                    pdf.set_font("DejaVu", "B", 16)
                    pdf.cell(0, 10, title, ln=True)
                    pdf.ln(4)
                    pdf.set_font("DejaVu", "", 12)
                    if isinstance(content, str):
                        pdf.multi_cell(0, 7, content)
                    else:
                        for item in content:
                            pdf.multi_cell(0, 7, f"• {str(item)}")
                            pdf.ln(1)
                    pdf.ln(6)

                write_section("Executive Summary", executive_summary)
                write_section("Key Insights", key_insights)
                write_section("Data Quality Issues", data_quality)
                write_section("Recommendations", recommendations)

                # Static charts for PDF
                pdf.set_font("DejaVu", "B", 16)
                pdf.cell(0, 10, "Generated Charts", ln=True)
                pdf.ln(5)

                for i, code in enumerate(chart_codes):
                    try:
                        # Try to extract x/y and type
                        chart_type = "scatter"
                        for t in ["bar", "line", "scatter", "pie", "histogram", "box", "area", "heatmap"]:
                            if f"px.{t}" in code:
                                chart_type = t
                                break
                        x_col, y_col = None, None
                        if "x=" in code:
                            x_col = code.split("x=")[1].split(",")[0].replace('"', '').replace("'", "").strip()
                        if "y=" in code:
                            y_col = code.split("y=")[1].split(",")[0].replace('"', '').replace("'", "").strip()

                        fig, ax = plt.subplots(figsize=(6, 4))
                        ax.set_facecolor("#f8f9fa")

                        if chart_type == "bar" and x_col and y_col:
                            ax.bar(df[x_col], df[y_col], color="#2a9d8f")
                        elif chart_type == "line" and x_col and y_col:
                            ax.plot(df[x_col], df[y_col], color="#264653", linewidth=2)
                        elif chart_type == "scatter" and x_col and y_col:
                            ax.scatter(df[x_col], df[y_col], color="#e76f51", s=50, alpha=0.8)
                        elif chart_type == "histogram" and x_col:
                            ax.hist(df[x_col], bins=15, color="#2a9d8f", edgecolor="white")
                        elif chart_type == "box" and y_col:
                            ax.boxplot(df[y_col].dropna())
                            ax.set_xticklabels([y_col])
                        elif chart_type == "pie" and y_col:
                            vals = df[y_col].value_counts()
                            ax.pie(vals, labels=vals.index, autopct='%1.1f%%')
                        elif chart_type == "heatmap":
                            if df.select_dtypes(include='number').shape[1] >= 2:
                                corr = df.corr(numeric_only=True)
                                im = ax.imshow(corr, cmap='coolwarm')
                                ax.set_xticks(range(len(corr.columns)))
                                ax.set_xticklabels(corr.columns, rotation=45, ha='right')
                                ax.set_yticks(range(len(corr.columns)))
                                ax.set_yticklabels(corr.columns)
                                fig.colorbar(im, ax=ax)
                            else:
                                ax.text(0.5, 0.5, "Not enough numeric data", ha='center', va='center')
                        else:
                            ax.text(0.5, 0.5, "Auto static render", ha='center', va='center')

                        # Always label charts
                        if x_col:
                            ax.set_xlabel(x_col)
                        if y_col:
                            ax.set_ylabel(y_col)
                        ax.set_title(f"Chart {i+1}: {chart_type.title()} Chart", fontsize=12)
                        plt.xticks(rotation=30, ha='right')

                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                            fig.savefig(tmp.name, bbox_inches='tight')
                            pdf.image(tmp.name, w=170)
                            os.remove(tmp.name)
                        plt.close(fig)
                        pdf.ln(10)

                    except Exception as e:
                        pdf.multi_cell(0, 7, f"Chart {i+1} error: {e}")
                        pdf.ln(5)

                # Regression chart in PDF
                try:
                    target_col = reg['target_variable']
                    feature_col = reg['feature_variable']
                    fig, ax = plt.subplots(figsize=(6, 4))
                    ax.scatter(df[feature_col], df[target_col], color='#2a9d8f', label='Data Points')

                    if df[feature_col].dtype != 'object' and df[target_col].dtype != 'object':
                        m, b = np.polyfit(df[feature_col], df[target_col], 1)
                        ax.plot(df[feature_col], m * df[feature_col] + b, color='#e76f51', label='Trendline')

                    ax.set_xlabel(feature_col)
                    ax.set_ylabel(target_col)
                    ax.set_title(f"Regression: {feature_col} vs {target_col}")
                    ax.legend()

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        fig.savefig(tmp.name, bbox_inches='tight')
                        pdf.image(tmp.name, w=170)
                        os.remove(tmp.name)
                    plt.close(fig)
                    pdf.ln(10)

                except Exception as e:
                    pdf.multi_cell(0, 7, f"Regression plot error: {e}")

                # Download button
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    pdf.output(tmp_pdf.name)
                    tmp_pdf_path = tmp_pdf.name

                with open(tmp_pdf_path, "rb") as f:
                    st.download_button(
                        label="📄 Download Full Report as PDF",
                        data=f.read(),
                        file_name="InsightAgent_Report.pdf",
                        mime="application/pdf"
                    )
                    os.remove(tmp_pdf_path)

            except Exception as e:
                st.error(f"PDF generation error: {e}")
    else:
        st.error("🚨 File has more than 4000 rows!")
else:
    st.write("📁 Upload a dataset to begin.")
