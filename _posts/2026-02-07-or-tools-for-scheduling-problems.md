---
title: Using OR-Tools for Scheduling Problems 
layout: post
category: software
---

I've been working on improving how we schedule maintenance in Akamai's cloud infrastructure with a focus on scheduling disruptive maintenance for hypervisor hosts, where we host hundreds of thousands of guest VMs. The prolem is quite complex and it involves understanding wide range of lmitations such as capacity constraints, customer disruption SLAs, and concurrency limits due to limited resources to do migrations in multiple levels (host, rack, datacenter etc.).

While developing prototypes for the solution, I tried various optimization tools including commercial and open-source Mixed Integer Programming (MIP) solvers. After trying out various options, I found that Google's OR-Tools library, particularly its CP-SAT solver, stood out as a great choice for tackling scheduling problems. In this post, I'll walk you through modeling a simple scheduling problem using OR-Tools and explain why it is a powerful tool for this type of problem.

## Maintenance Scheduling in Cloud Infrastructure

First off, let me explain the problem a bit more. As with any other attempt to benchmark a software, it's important to know that the results on this blog post are specific to the problem I'm trying to solve.

In cloud, there are physical servers called "hypervisor hosts" that run virtual machines (VMs) for customers. These hosts need to be maintained periodically to ensure security and reliability. Some of these maintenance tasks can be done with live patches (without a reboot), while others require all of the VMs on the host to be evacuated and then host to be rebooted. Handling live patches is relatively straightforward and the main focus is on safely rolling out updates. However, for maintenance that requires host reboot, VMs need to be migrated off to other hosts first, which brings the following challenges:

3Cs: Capacity, Concurrency, Conflict:

**Capacity**: You need to find a host with enough capacity to take the VMs. 

**Concurrency**: You need to make sure that the migration operations do not overload the network or storage systems, which can only handle a limited number of concurrent migrations.

**Conflict**: You need to make sure that the selected machine doesn't have VMs that would violate customer SLAs when migrated.

I'll be talking more about maintenance scheduling at SRECON26 in March. You can check out the conference page for more details: https://www.usenix.org/conference/srecon26americas/presentation/kutlay

## How to Model the Problem

Operation Research (OR) is a well-established field that focuses on using mathematical models, statistics, and algorithms to aid in decision-making. OR researchers have been working on scheduling problems for decades, and they have come up with various "problem types" that capture the essence of different scheduling challenges. Some of the well-known problem types include Job Shop Scheduling, Flow Shop Scheduling, and Resource-Constrained Project Scheduling. Knowing the right problem type to model your scheduling problem helps you to leverage the existing research and algorithms that have been developed for that problem type. It is likely that your problem won't exactly match one of the standard problem types, but you can often find a close enough match that allows you to use the existing tools and techniques effectively.

Maintenance scheduling in cloud is close to a Resource-Constrained Project Scheduling Problem (RCPSP) without the precedence constraints. In RCPSP, you have a set of tasks that need to be scheduled, each with its own duration and resource requirements. The goal is to find a schedule that minimizes the overall project duration while respecting resource constraints. Similarly in maintenance scheduling, each VM migration can be seen as a task that require certain resources (see 3Cs above) and the goal is to minimize the total time to complete all maintenance tasks.

## Modeling the Problem with OR-Tools CP-SAT Solver

OR-Tools is an open-source software suite developed by Google that provides a collection of tools for solving combinatorial optimization problems. One of its key components is the CP-SAT solver, which is a versatile portfolio solver that can handle a wide range of scheduling problems. For any given problem, CP-SAT tries to apply a wide range of algorithms to solve the problem and handles the information share in between them. CP-SAT does this because it is simply impossible to guess which algorithm will work best for a given problem (No Free Lunch Theorem). 

CP-SAT is particularly well-suited for scheduling problems because it has specialized variables and constraints that can model time, which makes the formulation of scheduling problems more intuitive and efficient. 

Let me give you code examples to illustrate this point. First, let's set up a toy problem for ourselves, where we have a single hypervisor host that needs to be maintained, and we have 3 VMs that need to be migrated off of it. Let's assume each migration takes 10 time units, and we want to consider solutions that can be completed within 100 time units.

```
hosts = ["host_1"]
vms = {"host_1": ["vm_1", "vm_2", "vm_3"]}
migration_duration = 10
planning_horizon = 100
```

The core of the problem is to schedule the migrations of these VMs while respecting the constraints related to capacity, concurrency, and conflict. Therefore, we need to model the timing of these migrations and the resources they consume. This is where CP-SAT's interval variables come in handy. In CP-SAT, you can use "interval variables" to represent tasks that have a start time, end time, and duration. Let's create an interval variable for each VM's migration, and save them in a dictionary for easy access later on.

```
vm_interval_vars = {} # Dictionary to hold interval variables for each VM

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
```

Executing the above code will give you a dictionary `vm_interval_vars` that contains interval variables for each VM's migration. Each interval variable has a start time, end time, and a fixed duration of 10 time units.

```
{
    'host_1': {
        'vm_1': vm_1_interval(start = vm_1_start, size = 10, end = vm_1_end), 
        'vm_2': vm_2_interval(start = vm_2_start, size = 10, end = vm_2_end), 
        'vm_3': vm_3_interval(start = vm_3_start, size = 10, end = vm_3_end)
    }
}
```

The interval variable allows you to then easily express constraints related to concurrency and resource usage. For example, you can use the `AddNoOverlap` constraint to ensure that no two migrations that require the same resource (e.g., network bandwidth) overlap in time. 

```
for host, vms_dict in vm_interval_vars.items():
    vm_intervals = list(vms_dict.values())
    model.AddNoOverlap(vm_intervals)
```

Or better, you can use the `AddCumulative` constraint to model the limited capacity of resources and ensure that the total resource usage at any given time does not exceed the available capacity. The costraint below sets a limit on the number of concurrent migrations that can happen at the same time. To match the `AddNoOverlap` constraint above, we can set the maximum number of concurrent migration to 1:

```
maximum_migrations_per_host = 1

for host, vms_dict in vm_interval_vars.items():
    vm_intervals = list(vms_dict.values())

    model.AddCumulative(
        vm_intervals,               # List of interval variables
        [1] * len(vm_intervals),    # Resource usage for each interval variable
        maximum_migrations_per_host # Maximum resource capacity
    )
```

The second argument in `AddCumulative` is the list of resource usages for each interval variable, which in this case is simply 1 for each migration since each migration consumes one unit of the resource. A more powerful use of AddCumulative would be to set different resource usages for different migrations, which is more useful to model real constraints like "throughput". If some VMs can be migrated with higher throughput than others, instead of limiting the number of concurrent migrations, you can limit the total throughput at any given time:

```
migration_throughput = {"vm_1": 5, "vm_2": 3, "vm_3": 2}
host_maximum_throughput = 5

for host, vms_dict in vm_interval_vars.items():
    vm_intervals = list(vms_dict.values())
    vm_throughputs = [migration_throughput[vm] for vm in vms_dict.keys()]

    model.AddCumulative(vm_intervals, vm_throughputs, host_maximum_throughput)
```

Since the maximum throughput is 5, we would expect the schedule to migrate VMs 2 and 3 at the same time, but not VM 1 with any other VM, since VM 1 alone consumes all the available throughput.

At this point, we have a tiny model that captures one aspect of the maintenance scheduling problem, which is the concurrency constraint. Let's solve this model and see what the solution looks like:

```
solver = cp_model.CpSolver()
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
```

The solution prints the start and end times for each VM's migration, which gives you a schedule that respects the concurrency constraint. 

```
CpSolverStatus.OPTIMAL
Schedule for host_1:
  vm_1: Start at 10, end at 20
  vm_2: Start at 0, end at 10
  vm_3: Start at 0, end at 10
```

As expected, we see VM 2 and VM 3 being migrated at the same time, while VM1 is migrated separately to respect the maximum throughput constraint.

## Why OR-Tools?

In order to understand why OR-Tools is a great choice, you need to understand the alternatives. One of the most common technique for solving scheduling problems is Mixed Integer Programming (MIP), which uses linear equations to represent the relationships between variables. There are many open-source MIP solvers out there but none of them gives you the tools to easily model time and scheduling constraints. 




## Modeling the Problem with Mixed Integer Programming (MIP)

Mixed Integer Programming (MIP) is the most commonly used technique for solving optimization problems. MIP models use linear equations to represent the relationships between variables, and they can handle both continuous and discrete variables. For example, you can use a binary variable to represent whether a VM is migrated at a specific time. Then, you can sum up the binary variables to count the total number of VMs migrated in a given time window, and add constraints to ensure that the number of concurrent migrations does not exceed the allowed limit.


