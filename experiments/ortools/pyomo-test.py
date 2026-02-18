import pyomo.environ as pyo
from pyomo.opt import SolverFactory

# Data
hosts = ["host_1"]
vms = {"host_1": ["vm_1", "vm_2", "vm_3"]}
planning_horizon = 100
migration_duration = 10
migration_throughput = {"vm_1": 5, "vm_2": 3, "vm_3": 2}
host_maximum_throughput = 5

# Create model
model = pyo.ConcreteModel()

# Sets
model.HOSTS = pyo.Set(initialize=hosts)
model.VMS = pyo.Set(initialize=vms["host_1"])
model.TIME = pyo.RangeSet(0, planning_horizon)

# Variables
# Start time for each VM migration
model.start = pyo.Var(model.VMS, domain=pyo.NonNegativeIntegers, 
                      bounds=(0, planning_horizon))

# Binary variable: is VM migrating at time t?
model.vm_active = pyo.Var(model.VMS, model.TIME, domain=pyo.Binary)

# Objective: Minimize makespan (completion time of last migration)
model.makespan = pyo.Var(domain=pyo.NonNegativeReals, bounds=(0, planning_horizon))
model.obj = pyo.Objective(expr=model.makespan, sense=pyo.minimize)

# Constraints

# Link start times to active periods
def active_constraint_rule(model, vm, t):
    """VM is active at time t if t is within [start, start+duration)"""
    return model.vm_active[vm, t] <= (
        1 if t >= 0 else 0
    ) * (model.start[vm] <= t) * (t <= model.start[vm] + migration_duration - 1)

# Since we can't use this exact form in linear constraints, we use big-M formulation
def active_start_rule(model, vm, t):
    """If t < start[vm], then active[vm,t] = 0"""
    M = planning_horizon
    return model.start[vm] <= t + M * (1 - model.vm_active[vm, t])

model.vm_active_start_con = pyo.Constraint(model.VMS, model.TIME, 
                                         rule=active_start_rule)

def active_end_rule(model, vm, t):
    """If t >= start[vm] + duration, then active[vm,t] = 0"""
    M = planning_horizon
    return t <= model.start[vm] + migration_duration - 1 + M * (1 - model.vm_active[vm, t])

model.vm_active_end_con = pyo.Constraint(model.VMS, model.TIME, 
                                       rule=active_end_rule)

def active_during_rule(model, vm):
    """If start <= t < start+duration, active can be 1"""
    # Sum of active bits must equal migration_duration
    return sum(model.vm_active[vm, tau] for tau in model.TIME) == migration_duration

model.vm_active_during_con = pyo.Constraint(model.VMS, rule=active_during_rule)

# Cumulative constraint: total throughput at any time <= host capacity
def cumulative_constraint_rule(model, t):
    """Total throughput demand at time t cannot exceed host capacity"""
    return sum(migration_throughput[vm] * model.vm_active[vm, t] 
               for vm in model.VMS) <= host_maximum_throughput

model.cumulative_con = pyo.Constraint(model.TIME, 
                                       rule=cumulative_constraint_rule)

# Makespan constraints
def makespan_constraint_rule(model, vm):
    """Makespan must be at least the end time of each VM"""
    return model.makespan >= model.start[vm] + migration_duration

model.makespan_con = pyo.Constraint(model.VMS, 
                                     rule=makespan_constraint_rule)

# Solve
solver = SolverFactory('appsi_highs')
solver.options['log_file'] = 'highs.log'
solver.options['log_to_console'] = True

results = solver.solve(model, tee=True)

# Print results
print("\nSolver Status:", results.solver.status)
print("Termination Condition:", results.solver.termination_condition)

if results.solver.termination_condition == pyo.TerminationCondition.optimal:
    print("\nOptimal solution found!")
    print(f"\nSchedule for host_1:")
    for vm in model.VMS:
        start = pyo.value(model.start[vm])
        end = start + migration_duration
        print(f"  {vm}: Start at {start}, end at {end}")
    print(f"\nMakespan: {pyo.value(model.makespan)}")
    
    # Optional: Print timeline
    print("\nTimeline (X = active migration):")
    for vm in model.VMS:
        timeline = ['.' for _ in range(planning_horizon + 1)]
        for t in model.TIME:
            if pyo.value(model.vm_active[vm, t]) > 0.5:
                timeline[t] = 'X'
        print(f"{vm}: {''.join(timeline[:30])}...")  # Show first 30 time units
        
elif results.solver.termination_condition == pyo.TerminationCondition.feasible:
    print("\nFeasible solution found!")
    for vm in model.VMS:
        start = pyo.value(model.start[vm])
        end = start + migration_duration
        print(f"  {vm}: Start at {start}, end at {end}")
else:
    print("\nNo solution found.")