import random
import time
import numpy as np
import task_processor

TDP = 95
CARBON_INTENSITY = {"KR": 310, "FR": 18}
LOG_FILE = "logs.txt"

def generate_tasks(num_tasks=20):
    tasks = []
    for i in range(num_tasks):
        task_time = random.randint(1, 20)
        cpu_usage = random.randint(10, 80)
        tasks.append({"name": f"Task{i+1}", "duration": task_time, "cpu": cpu_usage})
    return tasks

def simulate_schedule(a, b, c, d):
    task_processor.a_w = a
    task_processor.b_w = b
    task_processor.c_w = c
    task_processor.d_w = d

    total_time_sum = 0
    total_emission_sum = 0

    for trial_idx in range(3):
        for node in task_processor.nodes.values():
            node.assigned_time = 0
            node.current_cpu = 0
            node.tasks = []
            node.last_updated = time.time()

        tasks = generate_tasks()
        assigned_tasks_info = []

        for task in tasks:
            assigned_node_name = task_processor.process_task(task['name'], task['duration'], task['cpu'])
            if assigned_node_name:
                assigned_tasks_info.append((task, assigned_node_name))

        node_end_times = {"K3S1": 0, "K3S2": 0}
        total_emissions = 0

        for task, node_name in assigned_tasks_info:
            node_key = "KR" if "1" in node_name else "FR"
            ci = CARBON_INTENSITY[node_key]
            emission = task_processor.calculate_emission(task['cpu'], TDP, ci, task['duration'])
            total_emissions += emission

            node_id = "K3S1" if "1" in node_name else "K3S2"
            node = task_processor.nodes[node_id]
            node_end_times[node_id] = max(node_end_times[node_id], node.assigned_time)

        trial_time = max(node_end_times["K3S1"], node_end_times["K3S2"])
        total_time_sum += trial_time
        total_emission_sum += total_emissions

    avg_total_time = total_time_sum / 3
    avg_total_emission = total_emission_sum / 3

    score = avg_total_time + 1.5 * avg_total_emission
    return score

def gradient_descent(
    initial_params=np.array([1.0, 1.0, 1.0, 1.0]),
    lr=0.05,
    delta=0.01,
    max_steps=50
):
    params = initial_params.copy()
    history = []

    for step in range(max_steps):
        current_score = simulate_schedule(*params)
        gradients = []

        for i in range(len(params)):
            shifted = params.copy()
            shifted[i] += delta
            score_shifted = simulate_schedule(*shifted)
            grad = (score_shifted - current_score) / delta
            gradients.append(grad)

        gradients = np.array(gradients)
        params -= lr * gradients
        history.append((params.copy(), current_score))

        print(f"🌀 Step {step+1:02d} | Score: {current_score:.4f} | Params: {params}")

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"Step {step+1:02d} | Score: {current_score:.4f} | Params: {params.tolist()}\n")

    return params, history

if __name__ == "__main__":
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=== Gradient Descent Optimization Start ===\n")

    best_params, history = gradient_descent()

    print("\n✅ 최적 가중치:")
    for name, value in zip(["a_w", "b_w", "c_w", "d_w"], best_params):
        print(f"{name} = {value:.4f}")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{name} = {value:.4f}\n")

    print(f"\n📉 최소 목적 함수 값: {history[-1][1]:.4f}")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n📉 최소 목적 함수 값: {history[-1][1]:.4f}\n")
