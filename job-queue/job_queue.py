# job_queue.py

from queue import Queue

class JobQueue:
    def __init__(self):
        self.queue = Queue()
        self.status = {}

    def add_job(self, job):
        self.queue.put(job)
        self.status[job['id']] = 'PENDING'

    def get_job(self):
        if self.queue.empty():
            return None
        job = self.queue.get()
        self.status[job['id']] = 'RUNNING'
        return job

    def set_status(self, job_id, status):
        self.status[job_id] = status

    def get_status(self, job_id):
        return self.status.get(job_id, 'UNKNOWN')
