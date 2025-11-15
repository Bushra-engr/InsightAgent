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
import re
from smart_summary import get_Summary
from prompt import full_prompt

# page setup
st.set_page_config(page_title="Insight Agent", page_icon="🤖", layout="wide")

# css
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
</style>
""", unsafe_allow_html=True)

# api
API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-pro")

# header
st.title("INSIGHT AGENT 🤖📊")
st.header("Turn your Data into a Story")

# upload
data = st.file_uploader("Upload your dataset (Max 4000 rows)", type=["csv", "xls", "xlsx"])


def _choose_default_columns(df):
    num_cols = df.select_dtypes(include=np.number).columns.tolist()
    non_num = df.select_dtypes(exclude=np.number).columns.tolist()
    x = None
    y = None
    if num_cols:
        y = num_cols[0]
    if non_num:
        x = non_num[0]
    else:
        x = df.index.name if df.index.name else "index"
        if x == "index":
            df = df.reset_index()
            x = df.columns[0]
    return x, y, df


# --- TTS FIX FUNCTION ---
def clean_text(text):
    """remove emojis + non-ascii (gtts crashes on these)"""
    return re.sub(r'[^\x00-\x7F]+', ' ', text)


def speak_text(text):
    """safe text to speech wrapper for gTTS"""
    try:
        safe = clean_text(text)
        if safe.strip() == "":
            safe = "No summary available."

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpf:
            tts = gtts.gTTS(text=safe, lang='en')
            tts.save(tmpf.name)
            return tmpf.name

    except Exception as e:
        st.error(f"TTS Error: {e}")
        return None


# MAIN LOGIC
if data is not None:
    if data.name.endswith(".csv"):
        df = pd.read_csv(data)
    else:
        df = pd.read_excel(data)

    if df.shape[0] <= 4000:
        st.success("✅ File uploaded successfully!")
        st.dataframe(df.head(5), use_container_width=True)

        # summary
        smart_summary = get_Summary(df)

        # role & tone
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

            # tabs
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
                ["Smart Summary", "Key Insights", "Data Quality", "Recommendations", "Charts", "Regression"]
            )

            # --- FIXED TTS SECTION ---
            with tab1:
                st.info(executive_summary)

                audio_path = speak_text(executive_summary)
                if audio_path:
                    st.audio(audio_path, autoplay=True)

            with tab2:
                for text in key_insights:
                    st.write(text)

            with tab3:
                for text in data_quality:
                    st.write(text)

            with tab4:
                for text in recommendations:
                    st.write(text)

            # interactive charts
            with tab5:
                try:
                    scope_dict = {"df": df, "px": px}
                    for code in chart_codes:
                        exec(code, scope_dict)
                        fig = scope_dict.get("fig")
                        if fig is not None:
                            st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error in chart generation: {e}")

            # regression
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

            # PDF GENERATION (unchanged)
            try:
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.set_margins(15, 15, 15)
                pdf.add_page()

                base_path = os.path.join(os.getcwd(), "dejavu-fonts-ttf-2.37", "ttf")
                font_path_regular = os.path.join(base_path, "DejaVuSans.ttf")
                font_path_bold = os.path.join(base_path, "DejaVuSans-Bold.ttf")
                if os.path.exists(font_path_regular) and os.path.exists(font_path_bold):
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

                # charts → pdf
                pdf.set_font("DejaVu", "B", 16)
                pdf.cell(0, 10, "Generated Charts", ln=True)
                pdf.ln(5)

                for i, code in enumerate(chart_codes):
                    try:
                        chart_type = "scatter"
                        for t in ["bar", "line", "scatter", "pie", "histogram", "box", "area", "heatmap", "violin"]:
                            if f"px.{t}" in code:
                                chart_type = t
                                break

                        x_col = None
                        y_col = None
                        if "x=" in code:
                            x_col = code.split("x=")[1].split(",")[0].replace('"', '').replace("'", "").strip()
                        if "y=" in code:
                            y_col = code.split("y=")[1].split(",")[0].replace('"', '').replace("'", "").strip()

                        df_for_chart = df.copy()
                        if not x_col or x_col not in df_for_chart.columns:
                            default_x, default_y, df_for_chart = _choose_default_columns(df_for_chart)
                            if not x_col:
                                x_col = default_x
                            if not y_col:
                                y_col = default_y
                        if not y_col or y_col not in df_for_chart.columns:
                            numeric = df_for_chart.select_dtypes(include=np.number).columns.tolist()
                            if numeric:
                                y_col = numeric[0]

                        fig, ax = plt.subplots(figsize=(6, 4))
                        ax.set_facecolor("#f8f9fa")

                        if chart_type == "bar":
                            ax.bar(df_for_chart[x_col], df_for_chart[y_col], color="#2a9d8f")
                        elif chart_type == "line":
                            ax.plot(df_for_chart[x_col], df_for_chart[y_col], color="#264653", linewidth=2)
                        elif chart_type == "scatter":
                            ax.scatter(df_for_chart[x_col], df_for_chart[y_col], color="#e76f51", s=50, alpha=0.8)
                        elif chart_type == "histogram":
                            ax.hist(df_for_chart[x_col].dropna(), bins=15, color="#2a9d8f", edgecolor="white")
                        elif chart_type == "box":
                            ax.boxplot(df_for_chart[y_col].dropna())
                        elif chart_type == "pie":
                            vals = df_for_chart[y_col].value_counts()
                            ax.pie(vals, labels=vals.index, autopct='%1.1f%%')
                        elif chart_type == "heatmap":
                            numeric = df_for_chart.select_dtypes(include=np.number)
                            if numeric.shape[1] >= 2:
                                corr = numeric.corr()
                                im = ax.imshow(corr, cmap='coolwarm')
                                ax.set_xticks(range(len(corr.columns)))
                                ax.set_xticklabels(corr.columns, rotation=45)
                                ax.set_yticks(range(len(corr.columns)))
                                ax.set_yticklabels(corr.columns)
                                fig.colorbar(im, ax=ax)
                        elif chart_type == "area":
                            ax.fill_between(df_for_chart[x_col], df_for_chart[y_col], color="#2a9d8f", alpha=0.5)
                        elif chart_type == "violin":
                            ax.violinplot(df_for_chart[y_col].dropna())

                        ax.set_xlabel(x_col)
                        ax.set_ylabel(y_col)
                        ax.set_title(f"Chart {i+1}: {chart_type.title()}")
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

                # regression in pdf
                try:
                    target_col = reg['target_variable']
                    feature_col = reg['feature_variable']
                    fig, ax = plt.subplots(figsize=(6, 4))
                    ax.scatter(df[feature_col], df[target_col], color='#2a9d8f')
                    if df[feature_col].dtype != 'object' and df[target_col].dtype != 'object':
                        m, b = np.polyfit(df[feature_col], df[target_col], 1)
                        ax.plot(df[feature_col], m * df[feature_col] + b, color='#e76f51')
                    ax.set_xlabel(feature_col)
                    ax.set_ylabel(target_col)
                    ax.set_title(f"Regression: {feature_col} vs {target_col}")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        fig.savefig(tmp.name, bbox_inches='tight')
                        pdf.image(tmp.name, w=170)
                    os.remove(tmp.name)
                    plt.close(fig)
                    pdf.ln(10)
                except Exception as e:
                    pdf.multi_cell(0, 7, f"Regression plot error: {e}")

                # export pdf
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
