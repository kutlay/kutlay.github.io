from ortools.sat.python import cp_model
from pprint import pprint

model = cp_model.CpModel()

hosts = ["host_1"]
vms = {"host_1": ["vm_1", "vm_2", "vm_3"]}
planning_horizon = 1000
migration_duration = 10

vm_interval_vars = {}

for host in hosts:
    vm_interval_vars[host] = {}
    for vm in vms[host]:
        start_var = model.new_int_var(0, planning_horizon, f"{vm}_start")
        end_var = model.new_int_var(0, planning_horizon, f"{vm}_end")
        migration_duration = 10

        vm_interval_var = model.new_interval_var(
            start=start_var, size=migration_duration, end=end_var, name=f"{vm}_interval"
        )

        vm_interval_vars[host][vm] = vm_interval_var

migration_throughput = {"vm_1": 5, "vm_2": 3, "vm_3": 2}
host_maximum_throughput = 5

# Make sure the maximum migration throughput does not exceed 5
for host, vms_dict in vm_interval_vars.items():
    vm_intervals = list(vms_dict.values())
    vm_throughputs = [migration_throughput[vm] for vm in vms_dict.keys()]

    model.AddCumulative(vm_intervals, vm_throughputs, host_maximum_throughput)

solver = cp_model.CpSolver()
solver.parameters.log_search_progress = True
status = solver.Solve(model)
print(status)

# Print the schedule
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    for host, vms_dict in vm_interval_vars.items():
        print(f"Schedule for {host}:")
        for vm, interval_var in vms_dict.items():
            start = solver.Value(interval_var.StartExpr())
            end = solver.Value(interval_var.EndExpr())
            print(f"  {vm}: Start at {start}, end at {end}")
else:
    print("No solution found.")
