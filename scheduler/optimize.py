import optuna
import random
import time
import threading
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

        trial_end_k3s1 = node_end_times["K3S1"]
        trial_end_k3s2 = node_end_times["K3S2"]

        trial_emission = total_emissions
        trial_time = max(trial_end_k3s1, trial_end_k3s2)

        msg = f"\n🌱 Trial {trial_idx+1} 결과: 탄소 배출량 = {trial_emission:.2f}g, K3S1: {trial_end_k3s1:.1f}s, K3S2: {trial_end_k3s2:.1f}s, 총 소요 시간: {trial_time:.1f}s"
        print(msg)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

        total_time_sum += trial_time
        total_emission_sum += total_emissions

    avg_total_time = total_time_sum / 3
    avg_total_emission = total_emission_sum / 3

    score = avg_total_time + 1.5 * avg_total_emission

    return score


def objective(trial):
    a = trial.suggest_float("a_w", 1.0, 3.0)
    b = trial.suggest_float("b_w", 1.0, 3.0)
    c = trial.suggest_float("c_w", 1.0, 3.0)
    d = trial.suggest_float("d_w", 1.0, 10.0)

    score = simulate_schedule(a, b, c, d)

    log_line = f"Trial {trial.number} finished with value: {score:.4f} and parameters: {{'a_w': {a:.4f}, 'b_w': {b:.4f}, 'c_w': {c:.4f}, 'd_w': {d:.4f}}}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

    return score


if __name__ == "__main__":
    with open(LOG_FILE, "w") as f:
        f.write("=== Optuna Study Log Start ===\n")

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=1)

    print("\n✅ 최적 가중치:")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n✅ 최적 가중치:\n")

    for k, v in study.best_params.items():
        line = f"{k} = {v:.4f}"
        print(line)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    final_line = f"\n📉 최소 목적 함수 값: {study.best_value:.4f}"
    print(final_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(final_line + "\n")