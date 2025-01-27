# DICOM Image Analyzer

This project provides an end-to-end solution for analyzing DICOM (Digital Imaging and Communications in Medicine) images using a Flask-based REST API and a Streamlit-based frontend interface. The solution enables:

- Extraction of image features from DICOM files.
- Analysis of images to determine modality, body part, protocol, and direction using a LangChain model.
- Harmonization of DICOM metadata with LOINC codes.
- Display of analysis results in a user-friendly web interface.

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
  - [Backend API](#backend-api)
  - [Frontend Interface](#frontend-interface)
- [Endpoints](#endpoints)
- [How It Works](#how-it-works)
- [Technologies Used](#technologies-used)
- [Contributing](#contributing)
- [License](#license)

## Features

1. **REST API Backend**
   - Analyze DICOM images.
   - Harmonize DICOM metadata with LOINC codes.
   - Provide health checks and metadata about DICOM files.

2. **Frontend Interface**
   - Simple file uploader for users to upload DICOM files.
   - Real-time feedback on analysis results.

3. **Integration with LangChain LLM**
   - Use of a LangChain model to analyze image details based on encoded image prompts.

## Architecture

1. **Flask Backend**:
   - Handles DICOM file uploads and processes them.
   - Analyzes image content using the LangChain Ollama model.
   - Harmonizes metadata and attaches LOINC codes to DICOM files.

2. **Streamlit Frontend**:
   - Provides a web-based interface for users to upload and analyze DICOM files.
   - Displays results and communicates with the Flask backend via REST API calls.

3. **LangChain Ollama**:
   - Processes base64-encoded DICOM images to extract modality, body part, protocol, and direction.

## Installation

### Prerequisites

- Python 3.8+
- Pip
- Flask
- Streamlit
- pydicom
- LangChain integration libraries
- PIL (Python Imaging Library)

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/dicom-image-analyzer.git
   cd dicom-image-analyzer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the Flask backend:
   ```bash
   python app.py
   ```

4. Start the Streamlit frontend:
   ```bash
   streamlit run frontend.py
   ```

5. Access the web interface at `http://localhost:8501`.

## Usage

### Backend API

The Flask backend provides multiple endpoints to analyze and harmonize DICOM images. Refer to the [Endpoints](#endpoints) section for details.

### Frontend Interface

1. Open the Streamlit interface in your browser (`http://localhost:8501`).
2. Upload a DICOM file using the file uploader.
3. View the analysis results in real time.

## Endpoints

1. **`/` (GET)**
   - Returns API welcome message and available endpoints.

2. **`/v1/healthz` (GET)**
   - Returns API health status and uptime.

3. **`/v1/analyze` (POST)**
   - Accepts a DICOM file and returns analysis results, including:
     - Modality
     - Body Part
     - Protocol
     - Direction

4. **`/v1/harmonize` (POST)**
   - Accepts a DICOM file, analyzes it, and attaches relevant LOINC codes to the metadata.

5. **`/v1/pax` (POST)**
   - Returns the DICOM file's modality.

## How It Works

1. **File Upload**:
   - Users upload a DICOM file via the Streamlit interface.

2. **File Processing**:
   - The file is sent to the Flask backend.
   - The backend reads and decodes the DICOM image using `pydicom`.

3. **Image Analysis**:
   - The decoded image is normalized and converted to an 8-bit JPEG format.
   - A base64-encoded version of the image is sent to the LangChain Ollama model.
   - The model analyzes the image and extracts metadata.

4. **Harmonization**:
   - If harmonization is requested, relevant LOINC codes are determined based on the analysis results.
   - The codes are added to the DICOM file metadata.

5. **Result Display**:
   - Analysis results are returned to the Streamlit frontend.
   - Users can view the extracted metadata in JSON format.

## Technologies Used

- **Backend**:
  - Flask
  - Flask-CORS
  - pydicom

- **Frontend**:
  - Streamlit

- **AI Model**:
  - LangChain Ollama

- **Utilities**:
  - Pillow (PIL) for image processing
  - NumPy for numerical operations

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Commit your changes and push to your fork.
4. Submit a pull request with a detailed description of your changes.

