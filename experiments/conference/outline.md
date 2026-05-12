Introduction and Problem Context (1.5 min)

-Introducing our compute platform: size, heterogeneity, and operational goals. -Setting the context: thousands of long-lived VMs running on distributed hypervisor hosts. -Defining the core challenge: keeping hosts up-to-date (kernel/firmware updates, hardware replacement) while minimizing customer disruption and maintaining capacity.

Limitations of Existing Maintenance Approaches (1.5 min)
-Describing the baseline approaches previously used: manual scheduling and work overload on SREs -Summarizing the operational consequence: unpredictable customer impact, capacity degredation in datacenters, and delayed maintenance rollouts.

The Optimization Model (4 min)
Presenting the formulation of the problem, formulation of Resource-Constrained Project Scheduling Problem (RCPSP), a little bit of operations research primer. -Introducing key constraints and penalties of the model. -Concept of "customer disruption budget" (max simultaneous VM migrations per customer). -Objective: Minimize total campaign duration (complete all host maintenances as fast as possible).
Soft constraints for long notification periods (customer communication windows).
Briefly describe the solver, OR-tools, etc.

Deployment and Integration (4 min)
-Explaining integration with our orchestration and monitoring systems. -How schedules are generated and validated daily. -Continuous feedback from telemetry on migration durations and failure rates.

Lessons Learned and Challenges (2 min)
Balancing speed vs. predictability Iterative validation with SRE and operations teams to build trust. Handling changing capacity in active data centers.

Results, Future Work, and Closing (2 min)
Key outcomes: significant reduction in disruption per customer, faster maintenance completion, improved predictability. Closing thought: how optimization techniques can enhance reliability engineering and reduce maintenance risk across large infrastructures.


