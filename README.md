# AI Based Smart Infrastructure Monitoring System

An AI-powered web application for monitoring infrastructure records, managing building inspections, and detecting potential cracks in infrastructure images using a trained YOLO model.

## Project Overview

The AI Based Smart Infrastructure Monitoring System provides a centralized dashboard to manage infrastructure information, maintain inspection records, and analyze uploaded images for potential cracks.

The application combines a Flask web interface, an SQLite database, and a computer vision model to support infrastructure monitoring workflows.

## Features

- **Dashboard:** View infrastructure statistics, inspection summaries, and recent inspection records.
- **Infrastructure Management:** Add, view, edit, and delete infrastructure records.
- **Inspection Management:** Create, view, update, and delete building inspection records.
- **AI Image Analysis:** Upload infrastructure images and detect potential cracks using a trained YOLO model.
- **Annotated Results:** Generate and view images annotated with model detections.
- **Analysis History:** Store and retrieve previous AI analysis results, including confidence scores and image paths.
- **Input Validation:** Validate uploaded images and handle invalid requests.

## Technology Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite
- **Computer Vision:** OpenCV
- **AI Model:** Ultralytics YOLO
- **Development Environment:** Visual Studio Code

## Project Structure

```text
AI Based Smart Infrastructure Monitoring System/
├── app.py
├── database.py
├── ai_service.py
├── infrastructure.db
├── templates/
│   ├── dashboard.html
│   ├── infrastructure.html
│   └── inspection.html
├── static/
│   ├── style.css
│   └── uploads/
├── runs/
│   └── segment/
│       └── ai_models/
│           └── crack_seg/
│               └── weights/
│                   └── best.pt
└── README.md
```

*Note: The structure above highlights the main components. Additional files and folders may exist in the actual project.*

## Prerequisites

- Python installed on your system
- The project's Python dependencies
- The trained YOLO model file `best.pt`
- The project source files

## Installation and Setup

1. Clone or download the project repository.
2. Open the project folder in Visual Studio Code.
3. Open a terminal in the project directory.
4. Activate your existing virtual environment or create one.
5. Install the dependencies listed in the project's `requirements.txt`, if available.
6. Ensure the trained model exists at the path expected by `ai_service.py`.

### Run the Application

On Windows PowerShell, activate the virtual environment used by the project:

```powershell
.\ai_venv\Scripts\Activate.ps1
```

Then start the Flask application:

```powershell
python app.py
```

Open the following address in your browser:

```text
http://127.0.0.1:5000
```

*If your virtual environment has a different name, use its actual path.*

## How to Use

1. Open the dashboard.
2. Review the infrastructure and inspection statistics.
3. Open Infrastructure to manage building records.
4. Open Inspection to manage inspection records.
5. Use AI Image Analysis to upload an infrastructure image.
6. Review the detected crack labels, confidence scores, and annotated output image.
7. Open the analysis history to review previous results.

## Database

The application uses SQLite to store infrastructure records, inspection records, and AI analysis history. The database is initialized by the application through its database module.

## Limitations

- AI predictions depend on the quality and coverage of the training data and the uploaded image.
- Detection confidence is a model score, not a guarantee that a crack exists or a measure of structural safety.
- The system is a monitoring aid and is not a substitute for a qualified structural engineer's inspection.
- The trained model file and required Python packages must be available for AI analysis to work.

## Future Improvements

- Improve crack detection through additional training data and model evaluation.
- Add more comprehensive reporting and export capabilities.
- Strengthen automated testing and deployment procedures.

## Disclaimer

This project is intended for educational and infrastructure-monitoring purposes. AI predictions should be verified by qualified professionals before making structural safety decisions.