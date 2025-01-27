import re
import io
import time
import json
import base64
import logging
import decouple
import requests
import pydicom
import openai

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
        "endpoints": [
            f"/{API_VERSION}/healthz"
        ]
    }), 200

@app.route(f"/{API_VERSION}/healthz", methods=["GET"])
def health():
    uptime = time.time() - start_time
    response = {"message": "OK", "timestamp": int(time.time()), "uptime": int(uptime)}
    return jsonify(response), 200


def analyze_image(file_path_or_bytes):
    try:
        # If the input is a file path (str), open the file and read it as bytes
        if isinstance(file_path_or_bytes, str):
            with open(file_path_or_bytes, "rb") as f:
                file_bytes = f.read()
        else:
            # If the input is already bytes, use it directly
            file_bytes = file_path_or_bytes

        # Wrap the bytes in a file-like object
        image_buffer = io.BytesIO(file_bytes)

        # Decode the DICOM image
        ds = pydicom.dcmread(image_buffer)
        image = ds.pixel_array

        # Normalize the image and convert to 8-bit
        image_8bit = (
            (image - np.min(image)) / (np.max(image) - np.min(image)) * 255
        ).astype(np.uint8)

        # Convert the 8-bit array to a PIL image
        pil_image = Image.fromarray(image_8bit)

        # Save the PIL image as JPEG in memory
        img_byte_arr = io.BytesIO()
        pil_image.save(img_byte_arr, format="JPEG")
        img_byte_arr = img_byte_arr.getvalue()

        # Encode the image to base64
        encoded_image = base64.b64encode(img_byte_arr).decode("utf-8")

        # Define the prompt for Ollama
        prompt = f"""
        Given the following base64 encoded medical image, determine the following details:
        1. Modality ("CT" or "CR")
        2. Body Part ("Head" or "Chest")
        3. Protocol ("Contrast Enhanced" or "Non Contrast Enhanced")
        4. Direction ("Lateral" or "Sagittal" or "Axial" or "Coronal")
        
        Please provide the result in the following JSON format:
        {{
            "modality": "CT",  // or "CR" based on visual inspection
            "body_part": "Head",  // or "Chest" based on anatomical landmarks
            "protocol": "Contrast Enhanced",  // or "Non Contrast Enhanced" based on presence/absence of contrast agent
            "direction": "Sagittal"  // or "Axial" or "Coronal" based on the orientation of the image
        }}
        Base64 Image:
        data:image/jpeg;base64,{encoded_image}
        """

        # Use LangChain Ollama to generate a response
        llm = Ollama(model="deepseek-r1:1.5b")  # Specify the local model (e.g., `llama2`)
        response = llm(prompt)

        # Log the raw response for debugging
        logging.info(f"Ollama raw response: {response}")

        # Parse the response as JSON
        try:
            # Ensure the response is a dictionary before accessing its content
            if isinstance(response, dict) and "content" in response:
                response_text = response["content"]
            else:
                raise ValueError("Invalid response format: 'content' key missing")
            
            # Try to extract JSON from the response text
            try:
                match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
                if match:
                    json_text = match.group(1)
                    response_data = json.loads(json_text)
                else:
                    response_data = json.loads(response_text)
            except json.JSONDecodeError:
                logging.info(
                    "Using fallback response as the response text could not be parsed as JSON."
                )
                response_data = {
                    "modality": "NA",
                    "body_part": "NA",
                    "protocol": "NA",
                    "direction": "NA",
                }

        except Exception as e:
            logging.error(f"Error processing the response from Ollama: {e}")
            response_data = {
                "modality": "NA",
                "body_part": "NA",
                "protocol": "NA",
                "direction": "NA",
            }

        return response_data
    except Exception as e:
        raise ValueError(f"Error processing DICOM image: {e}")

@app.route(f"/{API_VERSION}/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        # Read the DICOM file and process it
        dicom_bytes = file.read()
        result = analyze_image(dicom_bytes)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error processing DICOM file: {e}")
        return jsonify({"error": str(e)}), 500


def send_to_pax(dicom_bytes, target_url=f"http://localhost:5000/{API_VERSION}/pax"):
    files = {"file": ("modified.dcm", dicom_bytes, "application/dicom")}
    response = requests.post(target_url, files=files)
    return response


@app.route(f"/{API_VERSION}/harmonize", methods=["POST"])
def harmonize():
    try:
        # Receive the file from the request
        file = request.files["file"]
        dicom_bytes = file.read()
        logging.info(f"Received DICOM file of size: {len(dicom_bytes)} bytes")

        # Analyze the image using OpenAI API
        analysis_result = analyze_image(dicom_bytes)
        logging.info(f"OpenAI analysis result: {analysis_result}")

        # Read the DICOM file from bytes
        ds = pydicom.dcmread(io.BytesIO(dicom_bytes))

        # Modify the headers based on analysis
        codeLOINC = ""
        codeMeaning = ""
        codingSchemaDesignator = "LN"
        codingSchemaVersion = "2.77"

        if analysis_result["body_part"] == "Head":
            if analysis_result["modality"] == "CT":
                if analysis_result["protocol"] == "Contrast Enhanced":
                    codeLOINC = "24727-0"
                    codeMeaning = "Head CT - with contrast"
                else:
                    codeLOINC = "30799-1"
                    codeMeaning = "Head CT - without contrast"
            else:
                logging.error("Invalid modality parameter for head")

        elif analysis_result["body_part"] == "Chest":
            if analysis_result["modality"] == "CT":
                if analysis_result["protocol"] == "Contrast Enhanced":
                    codeLOINC = "24628-0"
                    codeMeaning = "Chest CT - with contrast"
                else:
                    codeLOINC = "29252-4"
                    codeMeaning = "Chest CT - without contrast"

            elif analysis_result["modality"] == "XRAY":
                if analysis_result["direction"] == "Lateral":
                    codeLOINC = "39051-8"
                    codeMeaning = "Chest X-ray - LAT"
                else:
                    codeLOINC = "36572-6"
                    codeMeaning = "Chest X-ray – AP/PA"
            else:
                logging.error("Invalid modality parameter for chest")
        else:
            logging.error("Unknown body part parameter")

        if not codeLOINC or not codeMeaning:
            logging.error("Failed to determine LOINC code or meaning")

        # Add or update DICOM tags
        ds.add_new([0x0008, 0x0100], "SH", codeLOINC)
        ds.add_new([0x0008, 0x0102], "SH", codingSchemaDesignator)
        ds.add_new([0x0008, 0x0103], "SH", codingSchemaVersion)
        ds.add_new([0x0008, 0x0104], "LO", codeMeaning)
        dicom_bytes_modified = io.BytesIO()
        ds.save_as(dicom_bytes_modified)
        dicom_bytes_modified.seek(0)

        # Send the modified DICOM file to another API endpoint if you want
        # response = send_to_pax(dicom_bytes_modified)
        # return jsonify({"status": "success", "target_response": response.json()}), 200

        # Return the response from the target API
        return jsonify({"status": "success", "target_response": analysis_result}), 200

    except Exception as e:
        logging.error(f"Error processing DICOM file: {e}")
        return jsonify({"error": "internal_server_error", "message": str(e)}), 500


@app.route(f"/{API_VERSION}/pax", methods=["POST"])
def pax():
    try:
        # Mimic receiving the modified DICOM file
        file = request.files["file"]
        dicom_bytes = file.read()

        # For demonstration, just return a success message with some details
        ds = pydicom.dcmread(io.BytesIO(dicom_bytes))
        response = {
            "message": "DICOM file received successfully",
            "Modality": ds.Modality,
            # Include other relevant details as needed
        }

        return jsonify(response), 200

    except Exception as e:
        logging.error(f"Error receiving DICOM file: {e}")
        return jsonify({"error": "internal_server_error", "message": str(e)}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    response = {"error": "internal_server_error", "message": str(e)}
    return jsonify(response), 500


if __name__ == "__main__":
    logging.info("Starting the application ...")
    app.run(host="0.0.0.0", port=5000)
