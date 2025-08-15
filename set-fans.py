import os
import subprocess
import time


def find_hwmon(target_names=("nct6687", "it87", "superio")):
    hwmons = "/sys/class/hwmon"
    for hw in os.listdir(hwmons):
        name_file = f"{hwmons}/{hw}/name"
        try:
            with open(name_file) as f:
                name = f.read().strip()
            if any(target in name for target in target_names):
                return f"{hwmons}/{hw}"
        except FileNotFoundError:
            continue
    raise RuntimeError("No suitable hwmon found")


HWMON = find_hwmon()
pwms = [f"{HWMON}/pwm{i}_enable" for i in range(1, 9)]
pwm_values = [f"{HWMON}/pwm{i}" for i in range(1, 9)]

sys_min_temp = 45
sys_max_temp = 60

cpu_min_temp = 60
cpu_max_temp = 85

gpu_min_temp = 60
gpu_max_temp = 85

fan_min = 35
fan_max = 100


def set_manual_mode():
    for pwm_enable in pwms:
        try:
            with open(pwm_enable, "w") as f:
                f.write("1")
        except Exception as e:
            print(f"Could not set {pwm_enable} to manual: {e}")


def get_system_temp():
    output = subprocess.check_output(["sensors"]).decode()
    for line in output.splitlines():
        if line.strip().startswith("System:"):
            temp_str = line.split("+")[1].split("°C")[0]
            return float(temp_str)
    return None


def set_fan_speed(percent):
    pwm_val = int(2.55 * percent)
    for pwm_file in pwm_values:
        try:
            with open(pwm_file, "w") as f:
                f.write(str(pwm_val))
        except Exception as e:
            print(f"Could not write {pwm_file}: {e}")


def get_cpu_temp():
    output = subprocess.check_output(["sensors"]).decode()
    for line in output.splitlines():
        if "Tctl:" in line:
            temp_str = line.split("+")[1].split("°C")[0]
            return float(temp_str)
    return None


def get_gpu_temp():
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"]
        ).decode().splitlines()
        temps = [int(t) for t in output if t.strip()]
        return max(temps) if temps else gpu_min_temp
    except Exception as e:
        print("Could not read GPU temp:", e)
        return []


def temp_to_fan(temp, t_min, t_max):
    if temp <= t_min:
        return fan_min
    elif temp >= t_max:
        return fan_max
    else:
        return fan_min + (temp - t_min) * (fan_max - fan_min) / (t_max - t_min)


def get_percentage():
    cpu = temp_to_fan(get_cpu_temp(), cpu_min_temp, cpu_max_temp)
    gpu = temp_to_fan(get_gpu_temp(), gpu_min_temp, gpu_max_temp)
    sys = temp_to_fan(get_system_temp(), sys_min_temp, sys_max_temp)
    return max(cpu, gpu, sys)


if __name__ == "__main__":
    set_manual_mode()

    while True:
        set_fan_speed(get_percentage())
        time.sleep(0.1)
