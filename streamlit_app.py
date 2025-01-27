import streamlit as st
import requests

# Streamlit App Title
st.title("DICOM Image Analyzer")

# File Uploader
uploaded_file = st.file_uploader("Upload a DICOM file")

if uploaded_file is not None:
    st.write("File uploaded successfully!")

    # Display the file details
    st.write(f"Filename: {uploaded_file.name}")
    st.write(f"File size: {len(uploaded_file.read()) / 1024:.2f} KB")
    uploaded_file.seek(0)  # Reset file pointer

    # Upload to Flask Backend
    with st.spinner("Processing the image..."):
        try:
            files = {"file": uploaded_file}
            url = "http://127.0.0.1:5000/v1/analyze"  # Flask backend endpoint
            response = requests.post(url, files=files)

            if response.status_code == 200:
                result = response.json()
                st.success("Image analyzed successfully!")
                st.json(result)
            else:
                st.error("Error analyzing the image.")
                st.write(response.json())
        except Exception as e:
            st.error(f"Error: {e}")
