import pyomo.environ as pyo
from pyomo.opt import SolverFactory

# Data
vms = ["vm_1", "vm_2", "vm_3"]
migration_duration = 10
migration_throughput = {"vm_1": 5, "vm_2": 3, "vm_3": 2}
host_maximum_throughput = 5

model = pyo.ConcreteModel()

# Sets
model.VMS = pyo.Set(initialize=vms)
# Event points are indexed by VM (each VM contributes a start-event and an end-event)
# So event point e_k corresponds to start[vm_k]; there are |VMS| such points.
# We check the resource constraint at each start event (the tightest moments).
model.EVENTS = pyo.Set(initialize=vms)  # event point e[vm] = start[vm]

# Variables
model.start = pyo.Var(model.VMS, domain=pyo.NonNegativeReals)
model.end = pyo.Var(model.VMS, domain=pyo.NonNegativeReals)
model.makespan = pyo.Var(domain=pyo.NonNegativeReals)

# active[i, k] = 1 if task i is running at event point start[k]
model.active_vm = pyo.Var(model.VMS, model.EVENTS, domain=pyo.Binary)

# Objective
model.obj = pyo.Objective(expr=model.makespan, sense=pyo.minimize)

# Big-M: safe relative bound (sum of all durations)
M = len(vms) * migration_duration  # = 30


# 1. End definition
def end_def(model, vm):
    return model.end[vm] == model.start[vm] + migration_duration


model.end_def = pyo.Constraint(model.VMS, rule=end_def)


# 2. Makespan
def makespan_rule(model, vm):
    return model.makespan >= model.end[vm]


model.makespan_con = pyo.Constraint(model.VMS, rule=makespan_rule)

# 3. Link active[i,k] to whether task i is running at event point start[k].
#    Task i is active at event point start[k]  iff  start[i] <= start[k] < end[i].
#
#    We encode this with two big-M implications:
#
#    active[i,k] = 1  =>  start[i] <= start[k]       (i has started by event k)
#    active[i,k] = 1  =>  start[k] <  end[i]          (i has not yet finished)
#                    i.e. start[k] <= end[i] - epsilon
#    active[i,k] = 0  =>  no constraint forced
#
#    For MIP with continuous times we use:
#      start[i] <= start[k] + M*(1 - active[i,k])          ... (A)
#      start[k] <= end[i] - 1 + M*(1 - active[i,k])        ... (B)  (integer times)
#
#    AND the "must be active" direction: if both conditions hold, active must be 1.
#      start[k] - start[i] <= M * active[i,k]               ... (C)
#      end[i] - 1 - start[k] <= M * active[i,k]             ... (D)
#
#    Together (A)+(B) force active=0 when task i is outside the window,
#    and (C)+(D) force active=1 when task i is inside the window.


def active_lb_start(model, i, k):
    """(A): active=1 => start[i] <= start[k]"""
    return model.start[i] <= model.start[k] + M * (1 - model.active_vm[i, k])


model.active_lb_start_con = pyo.Constraint(
    model.VMS, model.EVENTS, rule=active_lb_start
)


def active_lb_end(model, i, k):
    """(B): active=1 => start[k] <= end[i] - 1"""
    return model.start[k] <= model.end[i] - 1 + M * (1 - model.active_vm[i, k])


model.active_lb_end_con = pyo.Constraint(model.VMS, model.EVENTS, rule=active_lb_end)


def active_ub_start(model, i, k):
    """(C): start[k] >= start[i] => active can be 1"""
    return model.start[k] - model.start[i] <= M * model.active_vm[i, k]


model.active_ub_start_con = pyo.Constraint(
    model.VMS, model.EVENTS, rule=active_ub_start
)


def active_ub_end(model, i, k):
    """(D): start[k] < end[i] => active can be 1"""
    return model.end[i] - 1 - model.start[k] <= M * model.active_vm[i, k]


model.active_ub_end_con = pyo.Constraint(model.VMS, model.EVENTS, rule=active_ub_end)


# 4. Resource constraint at each event point
def resource_rule(model, k):
    return (
        sum(migration_throughput[i] * model.active_vm[i, k] for i in model.VMS)
        <= host_maximum_throughput
    )


model.resource_con = pyo.Constraint(model.EVENTS, rule=resource_rule)

# Solve
solver = SolverFactory("appsi_highs")
solver.options["log_to_console"] = True
results = solver.solve(model, tee=True)

print("\nSolver Status:", results.solver.status)
print("Termination Condition:", results.solver.termination_condition)

if results.solver.termination_condition in (
    pyo.TerminationCondition.optimal,
    pyo.TerminationCondition.feasible,
):
    print(f"\nSchedule:")
    for vm in model.VMS:
        s = pyo.value(model.start[vm])
        e = pyo.value(model.end[vm])
        print(f"  {vm}: Start={s:.1f}, End={e:.1f}")
    print(f"\nMakespan: {pyo.value(model.makespan):.1f}")
else:
    print("\nNo solution found.")
