Hello everyone, thanks for joining the session, this is my first SREcon and it feels great to be here today.

- Start with the 10000 hosts case
- Multiple people working on the issues
- Different types of maintenance -> planned - unplanned - emergency 
- Migration types and disruption levels -> table of live migraiton - cold migration - warm migration

- Constraints and objective relationship of the model
- 

My name is Atalay Kutlay, I'm a senior software engineer at Akamai's Network Optimization team. My main focus at Akamai is to increase the efficiency of Akamai's fleet. I've worked on ranging from CDN capacity planning to virtual machine allocation, (pause) and most recently large scale maintenance scheduling, which I will be talking about today.

You may know Akamai as a CDN company, but we're a cloud provider now. We're in more than 50 datacenters, each having multiple types of hosts with various CPU generations, some with specialized cards like GPUs. 

As a cloud provider, our responsibility, and our SRE teams' job is to keep our fleet healthy and up-to-date. Therefore, we need to be on top of maintenance, which includes kernel, OS, firmware updates and preventative hardware maintenance. In most of these, the host needs to be rebooted and that can only happen once all the VMs are evacuated to another host.

we're not responsible for maintenance likelike .... software updates 
The way this happen ... 
Between sections have less words in between
Watch lightning talks
more on optimality
Questions:
- Data quality
- failure cases / drift 
- unsolvable problem
- what do sres do now?
 

In a typical maintenance, you have a old version host and you have some spare capacity that is already upgraded to the latest version. You start the maintenance by moving the VMs from the old version host to the new version host. At this point, the old version host is empty and ready to get the software update. The host that you migrated the VMs to is now part of the regular fleet. If the software update is successful, the old version host is now on the latest version and becomes spare capacity for the next host that will be updated. This process continues until all hosts are updated.

For one host, this sounds pretty simple, right? The challenge starts when you need to do a large number of these at the same time.

Let me explain this challenge of maintenance scheduling with a scenario. Imagine yourself as the SRE team that is responsible for Akamai's fleet. Now, on Monday morning, you get on a call with your boss who tells you that there is a new kernel version that has an important fix and there are 10,000 machines that need to be updated. There is no way to live patch this update, so the host needs to be rebooted, and all VMs need to be evacuated before the update. You have to notify the customers in advance, since the migration of their VMs will mean some downtime on their end. You have 90 days.

You get off the call, and start thinking: there are 10000 hosts and I have 90 days, so 100 hosts need to be updated daily. Since the hosts will be evacuated, you need enoguh capacity for these virtual machines to go, so you check capacity in each datacenter. You have tens of these datacenters. And then you think, which 100? There are many ways to pick hosts. What if you pick hosts which had all the webservers of a customer's website? Now you can potentially take down that customer's website while migrating the VMs. Also, what about the physical infrastructure? Can we evacuate all of these hosts at the same time? Do we have enough bandwidth for that? What if there are too many in a rack, will you cause a network bottleneck?

I hope you see that this is not a trivial problem. In fact, it's a quite complex scheduling problem which our SRE teams tackled manually with lots of effort and coordination. 
 
In this talk, I'll be sharing how we automated it. In this talk, I'll share how we created a new production service that generates maintenance schedules, integrates with FleetOps orchestration, and allows us to do optimal maintenance scheduling at scale.

-- 3:30 minutes

First, capacity. 
When evacuating a host, every VM on that host must be moved somewhere else. Ideally, these VMs are moved to hosts that are already running the latest software so they do not need to move again soon. At the same time, the datacenter cannot run out of available capacity, since that would prevent us from customers creating new VMs which means revenue loss. We need to make sure that the maintenance activity only uses a portion of the available capacity that we budgeted, so that we can keep the datacenter running smoothly while the maintenance is going on.

Second, conflicts. 
In cloud environments, some level of disruption is unavoidable — hosts fail, power outages happen, and occasionally entire regions experience outages. However, for a planned maintenance, any extreme disruption is unacceptable. Because we are trying to evacuate a lot of hosts at the same time, there is a risk of impacting some customer unfairly or asymmetricly. The "disruption budget" concept comes in handy to define what's an acceptable limit for the number of VMs or the percentage of VMs that can be migrated for each customer.  
The impact of the maintenance should always stay below this budget. 

This is challenging because each host has a variety of customers and host evacuation can cause different levels of disruption for different customers. For larger customers, a single VM is probably not that important, but for a smaller customer, that VM may be half of their workload. If the host selection is not done cleverly, we can end up in a situation where we try to migrate all the VMs a customer has at the same time, potentially causing them significant disruption.

Third, concurrency. 
Migrations are resource intensive operations. They entail copying large amounts of data from a host to another over the network. They use CPU, disk IO, and network bandwidth on the host. If too many migrations happen at the same time, it can cause network bottlenecks, performance issues and even cause the migrations to fail. So the host selection must account for the physical limits of the datacenter as well.

With these three constraints, maintenance scheduling becomes a complex scheduling problem with multiple constraints and an objective to minimize the total time to complete the updates. 

Well, now that we understand the problem, why don't we write an algorithm to solve it? 

-- 6:30 minutes

This is a classical scheduling problem which operations research has been studying for decades. The need to increase the efficiency of manufacturing processes has driven much of this research in the early 1900s and since then, scheduling is a key decision making process that's used on a regular basis in many manuacturing and services industries. The result of decades of research is a large number of well studied problem types and algorithms to solve them. You can think of similar problems to our maintenance scheduling problem, such as task scheduling problems in distributed systems or human resource scheduling to tasks in project management. 

Another product of decades of research is development of "hueristics" to many problem types, which are specialized algorithms that can find near optimal solutions. However, adapting these algorithms often requires expertise and time investment. A common approach to solve these problems is to model them mathematically and to u se mathematical solvers to get a solution. 

Let's take a look at how the maintenance scheduling problem can be formulated. The formulation is consists of 3 parts: variables, constraints, and the objective. Variables are the things that we want the solver to determine, based on the constraints that we set and the goal we have. Most people are familiar with Kubernetes or Terraform which adapts a declarative approach in creating infrastructure or deploying applications. You can think of the mathematical formulation as a "declarative" approach, where you define a desired state in which the schedule satisfies all the requirements and the solver is responsible for finding a way to achieve it. One of the benefits of this is that adding an extra constraint is an incremental process.

Now that we know the how to model it, we need a mathematical solver to find us the solution. 

Our solver of choice was OR-Tools' CP-SAT solver. OR-tools is an open source project developed by Google. It is capable of solving many types of problems, including linear programs, mixed integer linear program and it specializes in a couple of fields including vehicle routing problems and scheduling. One of the benefits of using CP-SAT over a mixed integer program solver is the easy to use interface thanks to the variables types specifically designed for scheduling problems. CP-SAT is able to define a "task" with start and end times (which we use for VM migrations) and then supports constraints such as "do only one at a time", or "do at most 2 at a time" etc. 

With this powerful engine, we created a new service called "Fleet Maintenance Planner" which is the brain of scheduling maintenances and its only task is to create a complete schedule for host maintenance every day. This keeps all the logic related to how we notify the customers, how we schedule a VM for migration, how to handle retries etc. and all of that already-existing expensive logic in the same components. But it only strips out the part related to the decision of "who", "what", and "when" to this new scheduler. So there is a separation in responsibilities between "how" things are done and "when" things are done.

Before I show you how we placed this service in our control plane, let me show you how the maintenance is scheduled before this service. Before this service, our SRE is responsible for understanding the available capacity in the datacenters. To start the maintanance, they need to get the list of hosts to be updated from the database, combine that with capacity availability and either check the customers on the hosts before scheduling a small percentage of the hosts to be updated. The biggest complexity and area for mistakes come from that decision making part.

Here is the diagram with the new "fleet maintenance planner" service. Our SRE still decides what hosts needs to be updated, but now, they are not responsible for making daily decisions on which ones to update. Instead, FleetOps takes the list of hosts entered by SRE and asks Fleet Maintenance Planner what needs to be updated in a daily cadence. With the schedule generated, FleetOps initiates the notifications and updates, and waits until next day to ask for the new set of hosts to be updated. In the meanwhile, Fleet Maintenance Planner gets feedback from the fleet regarding the previous updates, whether or they were successful. Again, it follows a declarative approach where we declare the hosts that needs to be on the latest version and the services find ways to get there. 

This service takes in the state of the fleet, from the status of hosts, and all the VMs on these hosts and produces a schedule with migration start and end times that satisfy all the constraitns that I've talked about so far. Our control plane takes this schedule and just follows it, scheduling migrations at the times that is specifies: and our SRE monitors the migrations happening successfully, only interacting with the system when a host fails to be evacuated or a software update goes south. 

An important thing to note here is that the planner runs on a a daily basis (or more frequently) to make decision based on as recent as possible data. For example, the capacity read out, to decide how many to schedule at any given time, needs to be fairly up to date with some headroom for failures. If we scheduled, say, all updates that will happen next month, we could run into issues if our update failure rate is much lower than expected. In its current design, what's expected to happen is the update pace to slow down automatically if our update failure rate is high, because the planner won't see enough spare capacity available the next time it runs. 

----------

It is often easy for a mathematical solver to find the thereotical minimum for an objective, in our case that would be the time that it takes to update the fleet, however it may not be able to find a solution that minimizes the objective as much. Because we know the solution and we can get the "optimal" time found by the mathematical solver, we can plot the difference in between, which shows you how much time the optimization model leaves on the table. 

A side benefit of having a model like this one is to be able to run scenarios. By manipulating the numbers that go into the model, you can answer questions like "What if we scale the datacenters by 2x tomorrow", "what if this customer scales 10x in this datacenter". And in fact, this is exactly how we decided how much spare capacity there needs to be in each datacenter. On this graph, you see the relationship between the spare capacity in our ORD2 datacenter on the x axis and the number of days it takes to update the datacenter on the Y axis. You see how the number of days go down significantly as we increase the spare capacity, until we reach 3% spare capacity. By producing these numbers in all of the datacenters we have, we had decided to have 3% spare capacity to reach our goal of updating our whole fleet under 90 days, which we aim to do by the next year under the Placement Group Aware Maintenance (PAM) program.

I hope this gave you a fair understanding of how to solve a complex scheduling problem with mathematical modeling and using a solver. This kind of framework could be useful in a lot of other problems that share similarities. You may not have all of the three (capacity, conflict, concurrency) problems that we have, but the framework would work even when one of them is missing. Examples could include in-place upgrade problems like how we install software on ghost which would only have the capacity and conflict constraints, or software rollout problems where you may not have capacity constraints if the update happens instantanously, but you may still want to limit the exposure of new softeware version to each customer in a balanced manner.

So for that, I also share an open source repository with examples of a couple scheduling problems that you can try to adapt to your problems. This includes the maintenance scheduling problem I've talked about today but it misses the internal details since it's an open source repository. If you're curious about the internal code, check out "fleet-maintenance-planner" on bits.linode.com
