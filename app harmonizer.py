import re
import io
import time
import json
import base64
import logging
import requests
import pydicom

import numpy as np

from PIL import Image
from flask_cors import CORS
from flask import Flask, jsonify, request
from langchain_community.llms import Ollama  # LangChain Ollama integration

# Initialize Flask app
API_VERSION = "v1"
app = Flask(__name__)
app.debug = True
CORS(app)

logging.basicConfig(level=logging.INFO)
start_time = time.time()

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Welcome to the Flask API!",
        "endpoints": [f"/{API_VERSION}/healthz", f"/{API_VERSION}/analyze", f"/{API_VERSION}/harmonize"]
    }), 200

@app.route(f"/{API_VERSION}/healthz", methods=["GET"])
def health():
    uptime = time.time() - start_time
    return jsonify({
        "message": "OK",
        "timestamp": int(time.time()),
        "uptime": int(uptime)
    }), 200

def analyze_image(file_path_or_bytes):
    try:
        # Read file as bytes
        file_bytes = (
            open(file_path_or_bytes, "rb").read() if isinstance(file_path_or_bytes, str) else file_path_or_bytes
        )

        # Decode DICOM image
        ds = pydicom.dcmread(io.BytesIO(file_bytes))
        image = ds.pixel_array

        # Normalize and convert to 8-bit
        image_8bit = ((image - np.min(image)) / (np.max(image) - np.min(image)) * 255).astype(np.uint8)
        pil_image = Image.fromarray(image_8bit)

        # Encode image to base64
        img_byte_arr = io.BytesIO()
        pil_image.save(img_byte_arr, format="JPEG")
        encoded_image = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

        # Define prompt for analysis
        prompt = f"""
        Given the following base64 encoded medical image, determine the following details:
        1. Modality ("CT" or "CR")
        2. Body Part ("Head" or "Chest")
        3. Protocol ("Contrast Enhanced" or "Non Contrast Enhanced")
        4. Direction ("Lateral", "Sagittal", "Axial", or "Coronal")
        
        Please provide the result in JSON format:
        {{
            "modality": "CT",
            "body_part": "Head",
            "protocol": "Contrast Enhanced",
            "direction": "Sagittal"
        }}
        Base64 Image:
        data:image/jpeg;base64,{encoded_image}
        """

        # Use LangChain Ollama
        llm = Ollama(model="deepseek-r1:1.5b")
        response = llm(prompt)

        # Extract JSON response
        if isinstance(response, dict) and "content" in response:
            response_text = response["content"]
            try:
                match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                return json.loads(response_text)
            except json.JSONDecodeError:
                logging.warning("Failed to parse JSON from response text.")
        return {
            "modality": "Unknown",
            "body_part": "Unknown",
            "protocol": "Unknown",
            "direction": "Unknown"
        }
    except Exception as e:
        logging.error(f"Error in analyze_image: {e}")
        raise ValueError("Error processing DICOM image")

@app.route(f"/{API_VERSION}/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    try:
        dicom_bytes = file.read()
        result = analyze_image(dicom_bytes)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error processing DICOM file: {e}")
        return jsonify({"error": str(e)}), 500

@app.route(f"/{API_VERSION}/harmonize", methods=["POST"])
def harmonize():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        dicom_bytes = file.read()
        analysis_result = analyze_image(dicom_bytes)

        ds = pydicom.dcmread(io.BytesIO(dicom_bytes))
        code_loinc, code_meaning = None, None

        if analysis_result["body_part"] == "Head":
            if analysis_result["modality"] == "CT":
                if analysis_result["protocol"] == "Contrast Enhanced":
                    code_loinc = "24727-0"
                    code_meaning = "Head CT - with contrast"
                else:
                    code_loinc = "30799-1"
                    code_meaning = "Head CT - without contrast"
        elif analysis_result["body_part"] == "Chest":
            if analysis_result["modality"] == "CT":
                if analysis_result["protocol"] == "Contrast Enhanced":
                    code_loinc = "24628-0"
                    code_meaning = "Chest CT - with contrast"
                else:
                    code_loinc = "29252-4"
                    code_meaning = "Chest CT - without contrast"
            elif analysis_result["modality"] == "XRAY":
                code_loinc = "39051-8" if analysis_result["direction"] == "Lateral" else "36572-6"
                code_meaning = "Chest X-ray - LAT" if analysis_result["direction"] == "Lateral" else "Chest X-ray - AP/PA"

        if not code_loinc or not code_meaning:
            raise ValueError("Unable to determine LOINC code or meaning")

        ds.add_new([0x0008, 0x0100], "SH", code_loinc)
        ds.add_new([0x0008, 0x0104], "LO", code_meaning)
        dicom_modified = io.BytesIO()
        ds.save_as(dicom_modified)

        return jsonify({"status": "success", "analysis": analysis_result}), 200

    except Exception as e:
        logging.error(f"Error in harmonize: {e}")
        return jsonify({"error": "internal_server_error", "message": str(e)}), 500

@app.route(f"/{API_VERSION}/pax", methods=["POST"])
def pax():
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        dicom_bytes = file.read()
        ds = pydicom.dcmread(io.BytesIO(dicom_bytes))

        return jsonify({
            "message": "DICOM file received successfully",
            "Modality": ds.Modality
        }), 200
    except Exception as e:
        logging.error(f"Error in pax: {e}")
        return jsonify({"error": "internal_server_error", "message": str(e)}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Unhandled exception: {e}")
    return jsonify({"error": "internal_server_error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

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

