---
title: Developing MIPs For Production Use
layout: post
category: software
---

I recently joined a new project to develop an optimization model for Linode's VM allocation system which can be summarized as a dynamic multi-dimensional bin packing problem where the items are VMs and the bins are hosts. The problem also has additional constraints to meet business goals (such as availability of certain plans, performance of VMs etc). We approach this problem using a Mixed Integer Program (MIP). If you are not familiar with MIPs, you can read [this article](https://www.gurobi.com/resources/mixed-integer-programming-mip-a-primer-on-the-basics/) by Gurobi which explains the basics very well.  MIPs are used in many resource allocation problems, such as airline scheduling or logistics. Learning about them will certainly give you a new aspect in approaching optimization.

Developing this kind of optimization model generally has two steps. First, you develop the model and show that it works on a small problem. Then, you build tooling to simulate the model in production, showing the benefits and side effects, trying to make sure everything is as you expected while also trying to show a case for such service in your organization.

If you can show some improvement (and convince people) then the next step is to create a way to develop the model in the long run, make it robust by working on tooling and tests, and finally wrap it nicely into a service. Making the underlying optimization model available as a service is a big part of solving this whole journey. Since you're optimizing an existing system, it is almost certain that the existing infrastructure will need to communicate with this optimization service while making decisions. The optimization model is only useful if others services can consume the results without distruptions and within an a reasonable time.

Requirements for such a service may include:

- A highly available API running the underlying optimization model on demand, providing various endpoints for a variety of use cases.
- Scheduled runs (e.g., every hour) where the solution of the optimization model is published for other systems to look up immediately
- Ability to make changes to the underlying model without distrupting the production service

I believe the set of requirements are pretty typical for services which exposes an underlying optimization model. In this post I try to explain what are the bare minimums to implement such a service. 

Let's start with the basics of the service and then I'll focus on what is needed to keep it running in the long term.

## Backend service design for long running processes

APIs typically shouldn't keep requests waiting for too long. Unfortunately, this is a problem for MIPs. They make take a long time (sometimes unpredictably) and fail. If the user of the API waits for an immediate response, the response time would vary a lot depending on the problem size and the failure wouldn't be easy to debug. Instead, the underlying optimization model should run as a background process and the client should have a way to check its status.

The simplified architecture of such long running operation would look like this:

![Life of long running processes](../assets/images/long-running-process.svg)

To learn more about long running processes, you can check out the [API Design Patterns](https://www.manning.com/books/api-design-patterns) book by JJ Geewax which has a "Long-running operations" section covering the basics for this kind of use case.

In addition to the long running process architecture, there are a couple more things to watch out for while developing a service on top of an optimization model.

First, make sure you limit the duration of the runs in some way. MIPs can take a long t Logging is key to understand what went wrong in these cases. Ideally, you should keep track of all the inputs and the outputs of the optimization model.

Second, implement retry strategies with varying MIP gap levels. There are cases where it makes sense to compromise the solution quality a little just to get a solution. Retries should consider increasing the MIP gap as well.

Lastly, monitor memory and CPU consumption closely. This is the case for all production services but MIPs require extra care. Make sure your deployment mechanism is flexible enough to increase memory and cores in the future if needed (more on this in the "stress testing" section below). For example, if you're deploying using a container system that only provisions 8GB of memory (smh), you really want to make sure your model will fit it even after a couple years down the line.

## Testing Optimization Models

This is where the fun begins. Optimization models can be hard to debug. Systematic approaches are necessary to allow consistent development of them. As a software engineer, I find it easier to think these tests in terms of traditional tests used in software engineering.

### Unit tests for optimization models

MIPs are consistent of sets, parameters, variables, constraints, and an objective function. Each of these are constructed using "code", and that code needs testing. It is very likely that your program doesn't get the input in the exact format that you need to feed to the optimization model so you manipulate data. Unit tests come into the picture at this phase to make sure the manipulation of the inputs are done correctly.

Utilizing concepts like [table driven tests](https://go.dev/wiki/TableDrivenTests) may help to get there faster.

### Functional Tests

How do you know your model works? Is it making the right decisions? Functional tests help to set a good basis for the basic functionality of the optimization model. 

The best way I've found so far to do this is to understand the fundamental problems that your model is solving and find very small examples of them. For example, if you're working on a bin packing problem, start with the very simple example of 2 bins and a couple of items. Compute the best possible allocation manually and keep them in [golden files](https://softwareengineering.stackexchange.com/questions/358786/what-are-golden-files). For more advanced "golden files", it helps to use the model first and vet the output. However, it is very easy to be tricked by a slightly wrong model output as it is quite hard for us humans to solve these problems manually. 

Lastly, add tests which go through these golden files, run the model, and expect the same output. These become extremely useful to be confident about changes to the model down the line. 

### Stress Tests

It is great that your model works today! What about in a year? Your business is (hopefully) growing fast so the problem is becoming more challenging for the optimization model every day. Assuming no improvements in the model, can it run for the upcoming years? Well, you need to scale up the inputs and see. 

Unfortunately there is no clear recipe for this kind of tests since every problem scales up in a different way. Therefore the first step is to figure out what's likely to grow and what's not, and just test for the worst case. As MIPs don't always scale well it may be very discouraging to see long run-times for your optimization model. Facing the reality with stress tests is hard but very productive. They often show you the weakest parts of the optimization model and help you to optimize them. 

Make sure you stress test your optimization model according to your problem's grow rate to be prepared for the problems in the future.

## Wrapping up

Mixed integer programming is a very powerful technique to solve allocations problems while expressing business goals in a simple way. They need a little extra care as the processing time and resources may be unpredictable when there is no vetting on the inputs. Maintaining them in the long run requires some tooling and specialized testing.

When planned well, they can serve a variety of use cases for many businesses. The challenges in developing them shouldn't discourage you from trying if you think a MIP is an answer to your problem.

## Helpful links

It's hard to find good content on MIPs in general but I think the following links are extremely valuable:

https://www.youtube.com/watch?v=i1wg23MFA5I&list=PLaoe2MTbJBvpFPyMMSOB-WrHofdHo3e74&ab_channel=MikeWagner (best introduction to LP and MIP for a software engineer that I could find)

https://www.nextmv.io/blog/the-road-to-production-is-paved-with-testing-and-experimentation

https://www.nextmv.io/blog/testing-testing-1-2-3 (on testing optimization model)

https://netflixtechblog.com/predictive-cpu-isolation-of-containers-at-netflix-91f014d856c7 (good use of MIP in production)