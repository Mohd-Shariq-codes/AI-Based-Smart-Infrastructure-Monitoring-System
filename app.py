
from pathlib import Path
import json
from uuid import uuid4

from flask import Flask, render_template, jsonify, request, url_for
from database import get_connection, initialize_database
from ai_service import analyze_image


# -------------------------
# Application Configuration
# -------------------------

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads" / "inspection_images"

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_SIZE

initialize_database()


# -------------------------
# Page Routes
# -------------------------

@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/infrastructure")
def infrastructure():
    return render_template("infrastructure.html")


@app.route("/inspection")
def inspection():
    return render_template("inspection.html")


@app.route("/alerts")
def alerts():
    return render_template("alerts.html")


@app.route("/reports")
def reports():
    return render_template("reports.html")


# -------------------------
# Shared Validation
# -------------------------

def is_registered_building(building_name, connection):
    row = connection.execute(
        "SELECT infrastructure_id FROM infrastructures WHERE name = ?",
        (building_name,)
    ).fetchone()

    return row is not None


# -------------------------
# AI Image Analysis API
# -------------------------

@app.route("/api/analyze-image", methods=["POST"])
def analyze_uploaded_image():
    uploaded_file = request.files.get("image")

    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({
            "success": False,
            "error": "Please select an image to analyze."
        }), 400

    extension = Path(uploaded_file.filename).suffix.lower().lstrip(".")

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({
            "success": False,
            "error": "Unsupported image format. Use JPG, JPEG, PNG or WEBP."
        }), 400

    # Read at most 5 MB plus one byte to validate actual file size.
    image_bytes = uploaded_file.stream.read(MAX_IMAGE_SIZE + 1)

    if not image_bytes:
        return jsonify({
            "success": False,
            "error": "The uploaded image is empty."
        }), 400

    if len(image_bytes) > MAX_IMAGE_SIZE:
        return jsonify({
            "success": False,
            "error": "Image size must not exceed 5 MB."
        }), 413

    # Generate our own filename instead of trusting the client filename.
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    upload_filename = f"{uuid4().hex}.{extension}"
    upload_path = UPLOAD_DIR / upload_filename

    try:
        with upload_path.open("wb") as image_file:
            image_file.write(image_bytes)

        # The AI service validates and analyzes the actual image.
        result = analyze_image(upload_path)

        original_image_url = url_for(
            "static",
            filename=f"uploads/inspection_images/{upload_filename}"
        )

        annotated_image_url = url_for(
            "static",
            filename=(
                f"uploads/analysis_results/"
                f"{result['result_filename']}"
            )
        )

        # Save successful AI analysis to database.
        analysis_id = uuid4().hex

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO ai_analysis_history (
                    analysis_id,
                    original_image,
                    annotated_image,
                    crack_count,
                    detections_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    original_image_url,
                    annotated_image_url,
                    result["crack_count"],
                    json.dumps(result["detections"])
                )
            )

        crack_count = result["crack_count"]

        if crack_count:
            message = (
                f"Analysis complete. The AI detected "
                f"{crack_count} possible crack detection(s)."
            )
        else:
            message = (
                "Analysis complete. No cracks were detected "
                "by the model at the current confidence threshold."
            )

        return jsonify({
            "success": True,
            "analysis_id": analysis_id,
            "message": message,
            "crack_count": crack_count,
            "detections": result["detections"],
            "original_image": original_image_url,
            "annotated_image": annotated_image_url
        }), 200

    except ValueError as error:
        app.logger.warning("Invalid image upload: %s", error)
        upload_path.unlink(missing_ok=True)

        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception:
        app.logger.exception("AI image analysis failed")
        upload_path.unlink(missing_ok=True)

        return jsonify({
            "success": False,
            "error": (
                "Image analysis failed. Please try another image "
                "or check the server terminal for details."
            )
        }), 500


# -------------------------
# Upload Size Error Handler
# -------------------------

@app.errorhandler(413)
def handle_file_too_large(error):
    return jsonify({
        "success": False,
        "error": "Image size must not exceed 5 MB."
    }), 413


# -------------------------
# AI Analysis History API
# -------------------------

@app.route("/api/ai-analysis-history", methods=["GET"])
def get_ai_analysis_history():
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    analysis_id,
                    original_image,
                    annotated_image,
                    crack_count,
                    detections_json,
                    created_at
                FROM ai_analysis_history
                ORDER BY id DESC
                LIMIT 50
                """
            ).fetchall()

        history = []

        for row in rows:
            record = dict(row)

            try:
                record["detections"] = json.loads(
                    record.pop("detections_json")
                )
            except (json.JSONDecodeError, TypeError):
                record["detections"] = []

            history.append(record)

        return jsonify({
            "success": True,
            "count": len(history),
            "history": history
        }), 200

    except Exception:
        app.logger.exception("Failed to load AI analysis history")

        return jsonify({
            "success": False,
            "error": "Could not load AI analysis history."
        }), 500


# -------------------------
# Dashboard API
# -------------------------

@app.route("/api/dashboard", methods=["GET"])
def get_dashboard_data():
    try:
        with get_connection() as connection:
            infrastructure_counts = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'Healthy' THEN 1 ELSE 0 END) AS healthy,
                    SUM(CASE WHEN status = 'Needs Inspection' THEN 1 ELSE 0 END)
                        AS needs_inspection,
                    SUM(CASE WHEN status = 'Warning' THEN 1 ELSE 0 END) AS warning,
                    SUM(CASE WHEN status = 'Critical' THEN 1 ELSE 0 END) AS critical
                FROM infrastructures
                """
            ).fetchone()

            inspection_counts = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END)
                        AS completed,
                    SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END)
                        AS pending,
                    SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END)
                        AS in_progress
                FROM inspections
                """
            ).fetchone()

            recent_inspections = connection.execute(
                """
                SELECT
                    inspection_id,
                    building_name,
                    inspection_date,
                    inspector_name,
                    status,
                    notes
                FROM inspections
                ORDER BY id DESC
                LIMIT 5
                """
            ).fetchall()

        return jsonify({
            "infrastructure": {
                "total": infrastructure_counts["total"] or 0,
                "healthy": infrastructure_counts["healthy"] or 0,
                "needs_inspection": infrastructure_counts["needs_inspection"] or 0,
                "warning": infrastructure_counts["warning"] or 0,
                "critical": infrastructure_counts["critical"] or 0
            },
            "inspections": {
                "total": inspection_counts["total"] or 0,
                "completed": inspection_counts["completed"] or 0,
                "pending": inspection_counts["pending"] or 0,
                "in_progress": inspection_counts["in_progress"] or 0
            },
            "recent_inspections": [
                dict(row) for row in recent_inspections
            ]
        })

    except Exception:
        app.logger.exception("Failed to load dashboard data")
        return jsonify({
            "error": "Could not load dashboard data."
        }), 500


# -------------------------
# Inspection API
# -------------------------

@app.route("/api/inspections", methods=["GET"])
def get_inspections():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM inspections ORDER BY id DESC"
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.route("/api/inspections", methods=["POST"])
def create_inspection():
    data = request.get_json(silent=True) or {}

    building_name = str(data.get("building_name", "")).strip()
    inspection_date = str(data.get("inspection_date", "")).strip()
    inspector_name = str(data.get("inspector_name", "")).strip()
    status = str(data.get("status", "Pending")).strip()
    notes = str(data.get("notes", "")).strip()

    if not building_name or not inspection_date or not inspector_name:
        return jsonify({
            "error": "Building, date and inspector name are required."
        }), 400

    allowed_statuses = {
        "Pending", "In Progress", "Completed", "Critical"
    }

    if status not in allowed_statuses:
        return jsonify({"error": "Invalid inspection status."}), 400

    try:
        with get_connection() as connection:
            if not is_registered_building(building_name, connection):
                return jsonify({
                    "error": "Please select a registered infrastructure."
                }), 400

            next_id = connection.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM inspections"
            ).fetchone()[0]

            inspection_id = f"INS-{next_id:03d}"

            connection.execute(
                """
                INSERT INTO inspections
                (inspection_id, building_name, inspection_date,
                 inspector_name, status, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    inspection_id,
                    building_name,
                    inspection_date,
                    inspector_name,
                    status,
                    notes
                )
            )

            row = connection.execute(
                "SELECT * FROM inspections WHERE inspection_id = ?",
                (inspection_id,)
            ).fetchone()

        return jsonify(dict(row)), 201

    except Exception:
        app.logger.exception("Failed to create inspection")
        return jsonify({"error": "Could not save the inspection."}), 500


@app.route("/api/inspections/<inspection_id>", methods=["PUT"])
def update_inspection(inspection_id):
    data = request.get_json(silent=True) or {}

    building_name = str(data.get("building_name", "")).strip()
    inspection_date = str(data.get("inspection_date", "")).strip()
    inspector_name = str(data.get("inspector_name", "")).strip()
    status = str(data.get("status", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if not building_name or not inspection_date or not inspector_name:
        return jsonify({
            "error": "Building, date and inspector name are required."
        }), 400

    allowed_statuses = {
        "Pending", "In Progress", "Completed", "Critical"
    }

    if status not in allowed_statuses:
        return jsonify({"error": "Invalid inspection status."}), 400

    try:
        with get_connection() as connection:
            if not is_registered_building(building_name, connection):
                return jsonify({
                    "error": "Please select a registered infrastructure."
                }), 400

            cursor = connection.execute(
                """
                UPDATE inspections
                SET building_name = ?, inspection_date = ?,
                    inspector_name = ?, status = ?, notes = ?
                WHERE inspection_id = ?
                """,
                (
                    building_name,
                    inspection_date,
                    inspector_name,
                    status,
                    notes,
                    inspection_id
                )
            )

            if cursor.rowcount == 0:
                return jsonify({"error": "Inspection not found."}), 404

            row = connection.execute(
                "SELECT * FROM inspections WHERE inspection_id = ?",
                (inspection_id,)
            ).fetchone()

        return jsonify(dict(row))

    except Exception:
        app.logger.exception("Failed to update inspection")
        return jsonify({"error": "Could not update the inspection."}), 500


@app.route("/api/inspections/<inspection_id>", methods=["DELETE"])
def delete_inspection(inspection_id):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM inspections WHERE inspection_id = ?",
            (inspection_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Inspection not found."}), 404

    return jsonify({"message": "Inspection deleted successfully."})


# -------------------------
# Infrastructure API
# -------------------------

@app.route("/api/infrastructures", methods=["GET"])
def get_infrastructures():
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM infrastructures ORDER BY id DESC"
        ).fetchall()

    return jsonify([dict(row) for row in rows])


@app.route("/api/infrastructures", methods=["POST"])
def create_infrastructure():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    location = str(data.get("location", "")).strip()
    status = str(data.get("status", "Healthy")).strip()
    condition = str(data.get("condition", "Good")).strip()
    last_inspection = str(data.get("last_inspection", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if not name or not location:
        return jsonify({
            "error": "Building name and location are required."
        }), 400

    if status not in {"Healthy", "Needs Inspection", "Warning", "Critical"}:
        return jsonify({"error": "Invalid infrastructure status."}), 400

    if not condition:
        return jsonify({"error": "Building condition is required."}), 400

    try:
        with get_connection() as connection:
            existing_ids = connection.execute(
                "SELECT infrastructure_id FROM infrastructures"
            ).fetchall()

            numeric_ids = []

            for row in existing_ids:
                value = row["infrastructure_id"]

                if value.startswith("INF-"):
                    try:
                        numeric_ids.append(int(value[4:]))
                    except ValueError:
                        pass

            infrastructure_id = f"INF-{max(numeric_ids, default=0) + 1:03d}"

            connection.execute(
                """
                INSERT INTO infrastructures
                (infrastructure_id, name, location, status,
                 condition, last_inspection, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    infrastructure_id, name, location, status,
                    condition, last_inspection, notes
                )
            )

            row = connection.execute(
                "SELECT * FROM infrastructures WHERE infrastructure_id = ?",
                (infrastructure_id,)
            ).fetchone()

        return jsonify(dict(row)), 201

    except Exception:
        app.logger.exception("Failed to create infrastructure")
        return jsonify({"error": "Could not save the infrastructure."}), 500


@app.route("/api/infrastructures/<infrastructure_id>", methods=["GET"])
def get_infrastructure(infrastructure_id):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM infrastructures WHERE infrastructure_id = ?",
            (infrastructure_id,)
        ).fetchone()

    if row is None:
        return jsonify({"error": "Infrastructure not found."}), 404

    return jsonify(dict(row))


@app.route("/api/infrastructures/<infrastructure_id>", methods=["PUT"])
def update_infrastructure(infrastructure_id):
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    location = str(data.get("location", "")).strip()
    status = str(data.get("status", "")).strip()
    condition = str(data.get("condition", "")).strip()
    last_inspection = str(data.get("last_inspection", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if not name or not location or not condition:
        return jsonify({
            "error": "Building name, location and condition are required."
        }), 400

    if status not in {"Healthy", "Needs Inspection", "Warning", "Critical"}:
        return jsonify({"error": "Invalid infrastructure status."}), 400

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE infrastructures
                SET name = ?, location = ?, status = ?,
                    condition = ?, last_inspection = ?, notes = ?
                WHERE infrastructure_id = ?
                """,
                (
                    name, location, status, condition,
                    last_inspection, notes, infrastructure_id
                )
            )

            if cursor.rowcount == 0:
                return jsonify({"error": "Infrastructure not found."}), 404

            row = connection.execute(
                "SELECT * FROM infrastructures WHERE infrastructure_id = ?",
                (infrastructure_id,)
            ).fetchone()

        return jsonify(dict(row))

    except Exception:
        app.logger.exception("Failed to update infrastructure")
        return jsonify({"error": "Could not update the infrastructure."}), 500


@app.route("/api/infrastructures/<infrastructure_id>", methods=["DELETE"])
def delete_infrastructure(infrastructure_id):
    try:
        with get_connection() as connection:
            # Find the infrastructure before attempting deletion.
            infrastructure = connection.execute(
                """
                SELECT infrastructure_id, name
                FROM infrastructures
                WHERE infrastructure_id = ?
                """,
                (infrastructure_id,)
            ).fetchone()

            if infrastructure is None:
                return jsonify({
                    "error": "Infrastructure not found."
                }), 404

            # Keep infrastructure records that have inspection history.
            linked_inspections = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM inspections
                WHERE building_name = ?
                """,
                (infrastructure["name"],)
            ).fetchone()["total"]

            if linked_inspections > 0:
                return jsonify({
                    "error": (
                        f'Cannot delete "{infrastructure["name"]}" because '
                        f'{linked_inspections} inspection record(s) are linked '
                        "to this building. Preserve the inspection history "
                        "by keeping this infrastructure record."
                    ),
                    "code": "INFRASTRUCTURE_HAS_INSPECTIONS",
                    "linked_inspections": linked_inspections
                }), 409

            # Delete only when no inspection history references its name.
            connection.execute(
                """
                DELETE FROM infrastructures
                WHERE infrastructure_id = ?
                """,
                (infrastructure_id,)
            )

        return jsonify({
            "message": "Infrastructure deleted successfully."
        }), 200

    except Exception:
        app.logger.exception("Failed to delete infrastructure")
        return jsonify({
            "error": "Could not delete the infrastructure."
        }), 500


# -------------------------
# Run Application
# -------------------------

if __name__ == "__main__":
    app.run(debug=True)
