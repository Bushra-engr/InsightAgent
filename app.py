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

# Custom modules
from smart_summary import get_Summary
from prompt import full_prompt

# PAGE SETUP & STYLE
st.set_page_config(page_title="Insight Agent", page_icon="🤖", layout="wide")

st.markdown("""
<style>
:root {
    --primary-color: #264653;
    --secondary-color: #2a9d8f;
    --background-light: #f1f5f2;
    --panel-color: #d9e4dd;
    --text-dark: #0b0c0c;
    --header-color: #1b263b;
}
.stApp { background-color: var(--background-light); }
h1 { color: var(--header-color); text-align: center; font-weight: 800; }
div[data-testid="stFileUploader"] {
    background-color: var(--panel-color);
    border: 2px dashed var(--secondary-color);
    padding: 1em;
    border-radius: 10px;
}
div.stButton > button:first-child {
    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
    color: white; font-weight: 600; border-radius: 8px; transition: 0.3s;
}
div.stButton > button:first-child:hover {
    background: linear-gradient(90deg, var(--secondary-color), var(--primary-color));
    transform: scale(1.03);
}
</style>
""", unsafe_allow_html=True)


# API CONFIG
API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-pro")

# APP HEADER
st.title("INSIGHT AGENT 🤖📊")
st.header("Turn your Data into a Story")

# DATA UPLOAD
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

            with tab5:
                try:
                    scope_dict = {"df": df, "px": px}
                    for code in chart_codes:
                        exec(code, scope_dict)
                        fig = scope_dict["fig"]
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error in chart generation: {e}")

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

            # PDF GENERATE
            try:
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.set_margins(15, 15, 15)
                pdf.add_page()

                base_path = os.path.join(os.getcwd(), "dejavu-fonts-ttf-2.37", "ttf")
                font_path_regular = os.path.join(base_path, "DejaVuSans.ttf")
                font_path_bold = os.path.join(base_path, "DejaVuSans-Bold.ttf")

                if not (os.path.exists(font_path_regular) and os.path.exists(font_path_bold)):
                    st.error("⚠️ Font files missing! Make sure both DejaVuSans.ttf and DejaVuSans-Bold.ttf exist in your ttf folder.")
                else:
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

                    pdf.set_font("DejaVu", "B", 16)
                    pdf.cell(0, 10, "Generated Charts", ln=True)
                    pdf.ln(5)

                    for i, code in enumerate(chart_codes):
                        try:
                            scope_dict = {"df": df, "px": px}
                            exec(code, scope_dict)
                            fig = scope_dict["fig"]
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                                try:
                                    fig.write_image(tmp.name, format='png', engine='kaleido', scale=2)
                                except Exception:
                                    try:
                                        fig.write_html(tmp.name + ".html")
                                        fig.write_image(tmp.name, format='png', engine='orca')
                                    except Exception as alt_e:
                                        pdf.multi_cell(0, 7, f"Chart {i+1} skipped (no image export available: {alt_e})")
                                        continue
                                img_path = tmp.name
                            pdf.set_font("DejaVu", "B", 12)
                            pdf.cell(0, 8, f"Chart {i+1}", ln=True)
                            pdf.image(img_path, w=170)
                            pdf.ln(10)
                            os.remove(img_path)
                        except Exception as e:
                            pdf.multi_cell(0, 7, f"Chart {i+1} error: {e}")
                            pdf.ln(5)

                    try:
                        target_col = reg['target_variable']
                        feature_col = reg['feature_variable']
                        has_statsmodels = importlib.util.find_spec("statsmodels") is not None
                        if has_statsmodels:
                            reg_fig = px.scatter(df, x=feature_col, y=target_col, trendline='ols',
                                                 trendline_color_override='red')
                        else:
                            reg_fig = px.scatter(df, x=feature_col, y=target_col)
                            reg_fig.update_traces(marker=dict(color='blue'))
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                            try:
                                reg_fig.write_image(tmp.name, format='png', engine='kaleido', scale=2)
                            except Exception:
                                try:
                                    reg_fig.write_html(tmp.name + ".html")
                                    reg_fig.write_image(tmp.name, format='png', engine='orca')
                                except Exception as alt_e:
                                    pdf.multi_cell(0, 7, f"Regression skipped (export error: {alt_e})")
                                    continue
                            reg_img = tmp.name
                        pdf.set_font("DejaVu", "B", 16)
                        pdf.cell(0, 10, "Regression Analysis", ln=True)
                        pdf.image(reg_img, w=170)
                        os.remove(reg_img)
                    except Exception as e:
                        pdf.multi_cell(0, 7, f"Regression plot error: {e}")

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                        pdf.output(tmp_pdf.name)
                        tmp_pdf_path = tmp_pdf.name

                    with open(tmp_pdf_path, "rb") as f:
                        pdf_output = f.read()
                        st.download_button(
                            label="📄 Download Full Report as PDF",
                            data=pdf_output,
                            file_name="InsightAgent_Report.pdf",
                            mime="application/pdf"
                        )
                        os.remove(tmp_pdf_path)

            except Exception as e:
                st.error(f"PDF generation error: {e}")

    else:
        st.error("🚨 Error: File has more than 4000 rows!")
else:
    st.write("📁 No file selected yet.")
