# server/app.py
from flask import Flask, request, jsonify
from job_queue import JobQueue
app = Flask(__name__)
queue = JobQueue()

@app.route("/jobs", methods=["POST"])
def add_job():
    job = request.json
    queue.add_job(job)
    return {"message": "Job added", "id": job["id"]}, 201

@app.route("/jobs/next", methods=["GET"])
def get_next_job():
    job = queue.get_job()
    if job:
        return jsonify(job)
    else:
        return {"message": "No job available"}, 204

@app.route("/jobs/<job_id>/status", methods=["POST"])
def update_status(job_id):
    status = request.json.get("status")
    queue.set_status(job_id, status)
    print(f"Status updated to {status}")
    return {"message": f"Status updated to {status}"}, 200

@app.route("/jobs/<job_id>/status", methods=["GET"])
def get_status(job_id):
    status = queue.get_status(job_id)
    return {"status": status}, 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)
