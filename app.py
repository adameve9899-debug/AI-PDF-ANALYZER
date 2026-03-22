import streamlit as st
from openai import OpenAI
import pandas as pd
import PyPDF2
import io
import json
import time

st.set_page_config(page_title="PDF to Excel AI Analyzer", layout="centered")
st.title("📄 Universal AI PDF Analyzer")
st.markdown("Powered by OpenRouter / Universal APIs")

# --- Updated to ask for an OpenRouter Key ---
api_key = st.text_input("Enter your OpenRouter API Key:", type="password")

uploaded_files = st.file_uploader("Upload PDFs (Batch process as many as you need)", type="pdf", accept_multiple_files=True)

format_options = {
    "Summary Report": "Extract the main topic, key findings, and a brief summary.",
    "Financial Data": "Extract company name, revenue, expenses, and net profit.",
    "Invoice Details": "Extract vendor name, invoice date, total amount, and line items.",
    "Custom": "User defined"
}

chosen_format = st.selectbox("Choose the Output Format:", list(format_options.keys()))

if chosen_format == "Custom":
    ai_instruction = st.text_area("Describe exactly what information the AI should extract as columns:")
else:
    ai_instruction = format_options[chosen_format]

# --- THE MAGIC HAPPENS HERE ---
def analyze_pdf(text, instruction, api_key):
    # We use the OpenAI library, but point it to OpenRouter!
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    prompt = f"""
    Analyze the following text and extract information based on this instruction: '{instruction}'.
    Return the extracted data STRICTLY as a flat JSON object (key-value pairs) with no markdown formatting.
    Text: {text[:25000]} 
    """
    
    try:
        # We are using Nvidia's incredibly powerful free model hosted on OpenRouter
        response = client.chat.completions.create(
            model="nvidia/nemotron-3-super:free", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        result_text = response.choices[0].message.content
        return json.loads(result_text.strip().replace("json", "").replace("", ""))
    except Exception as e:
        return {"Error": f"Failed to parse data. {str(e)}"}

# --- The rest of the logic stays the same! ---
if st.button("Analyze PDFs & Generate Excel"):
    if not api_key or not uploaded_files:
        st.error("Please enter your API key and upload PDFs.")
    else:
        with st.spinner(f"Analyzing {len(uploaded_files)} PDFs..."):
            all_data = []
            progress_bar = st.progress(0)
            
            for i, file in enumerate(uploaded_files):
                reader = PyPDF2.PdfReader(file)
                text = "".join([page.extract_text() + "\n" for page in reader.pages if page.extract_text()])
                
                # Pass the API key to our new function
                data = analyze_pdf(text, ai_instruction, api_key)
                data["Source File"] = file.name
                all_data.append(data)
                
                progress_bar.progress((i + 1) / len(uploaded_files))
                
                # Small pause to respect OpenRouter's 20 requests/minute free limit
                if len(uploaded_files) > 1:
                    time.sleep(3) 
            
            df = pd.DataFrame(all_data)
            cols = ['Source File'] + [col for col in df.columns if col != 'Source File']
            df = df[cols]
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='AI Report')
            
            st.success("Analysis Complete!")
            st.dataframe(df)
            st.download_button("📥 Download Excel Report", output.getvalue(), "AI_Report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
