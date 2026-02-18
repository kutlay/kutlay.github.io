import pyomo.environ as pyo
import time

# Define the model
model = pyo.ConcreteModel()

# Sets
model.I = pyo.Set(initialize=range(1, 501))  # 50 items
model.J = pyo.Set(initialize=range(1, 201))  # 20 bins

# Parameters
import random
random.seed(42)
model.c = pyo.Param(model.I, model.J, initialize={(i,j): random.uniform(1, 10) for i in model.I for j in model.J})  # costs
model.demand = pyo.Param(model.I, initialize={i: random.uniform(10, 100) for i in model.I})
model.capacity = pyo.Param(model.J, initialize={j: random.uniform(100, 500) for j in model.J})

# Variables
model.x = pyo.Var(model.I, model.J, domain=pyo.NonNegativeReals)  # Decision: quantity of item i allocated to bin j

# Objective: minimize cost
def obj_rule(model):
    return sum(model.c[i,j] * model.x[i,j] for i in model.I for j in model.J)
model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

# Constraints
def demand_rule(model, i):
    return sum(model.x[i,j] for j in model.J) == model.demand[i]  # Demand satisfaction for each item
model.demand_constraint = pyo.Constraint(model.I, rule=demand_rule)

def capacity_rule(model, j):
    return sum(model.x[i,j] for i in model.I) <= model.capacity[j]  # Capacity of each bin
model.capacity_constraint = pyo.Constraint(model.J, rule=capacity_rule)

# Solver
solver = pyo.SolverFactory('appsi_highs')

# Cold Start (no warm start)
start_time_cold = time.time()
solver.solve(model, tee=False)
end_time_cold = time.time()

# Store results of cold start
cold_solution = {(i,j): pyo.value(model.x[i,j]) for i in model.I for j in model.J}
cold_time = end_time_cold - start_time_cold

solver = pyo.SolverFactory('appsi_highs')
# Now for the warm start:
# Set the initial values as the solution of the cold start
for i in model.I:
    for j in model.J:
        model.x[i,j].set_value(cold_solution[i, j])

# Warm Start (with initial solution)
start_time_warm = time.time()
solver.solve(model, tee=False)
end_time_warm = time.time()

warm_time = end_time_warm - start_time_warm

# Results
print(f"Cold start solve time: {cold_time:.4f} seconds")
print(f"Warm start solve time: {warm_time:.4f} seconds")

if warm_time < cold_time:
    print("Warm start was faster!")
else:
    print("Cold start was faster or there was no significant difference.")

