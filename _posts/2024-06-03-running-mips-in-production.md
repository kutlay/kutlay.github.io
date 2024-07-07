---
title: Running MIPs in Production 
layout: post
category: software
---

Recently I joined a new project to develop an optimization model for Linode's VM allocation problem. The problem can be summarized as a multi dimensional bin packing problem with extra constraints. We solve this problem using Mixed Integer Program (MIP). MIPs are used in many resource allocations problems, such as airline scheduling or logistics. 

Making the underlying optimization model available as a service is a big part of solving this whole problem. The optimization model is only useful if other services who are in charge of allocation operations (such as creating a new VM, migrating a VM etc.) can use it effectively. Here are the requirements for the service:

- Highly available API which runs the same underlying model on-demand with different sets of inputs using different endpoints
- Scheduled (such as every hour) runs where the results are published for other system's to lookup immediately
- Ability to make changes to the underlying model in much higher cadence since the company is just started to focus on the problem

I believe these set of requirements are very typical for a production grade service which exposes an underlying optimization model. In this post I will try to explain what are the bare minimums to implement such service.

## Backend service design for long running operations

The only part that makes this service different than any other REST API backend is the fact that MIPs can take a long time. REST APIs typically shouldn't keep the requests waiting for too long. Instead, the underlying optimization model should be run as a background process and the client should have a way to check the status.

The very simple architecture looks like this:

![Life of long running processes](../assets/images/long-running-process.svg)

The exact implementation depends on how much complexity you're willing to work with. [API Design Patterns](https://www.manning.com/books/api-design-patterns) book by JJ Geewax has a "Long-running operations" section which covers the basics for this kind of use case. Check it out!

Some things to watch out for:

Make sure you limit the duration of the runs by "something". MIPs can take a long time for the most unexpected instances of runs. Make sure you log these cases!

Implement retry strategies with varying MIP gap levels if needed. There are cases where it makes sense to compromise the solution quality a little just to get a solution. Retries should consider increasing the MIP gap as well.

Monitor memory and CPU consumption closely. This is the case for all production services but MIPs require extra care. Make sure your deployment mechanism is flexible enough to increase memory and cores in the future if needed (more on this in the "stress testing" section below). For example, if you're deploying using a container system that only provisions 8GB of memory (smh), you really want to make sure your model will fit it even after a couple years down the line.

## Testing

This is where the fun begins. Optimization models can be hard to debug. Systematic approaches are necessary to allow consistent development of them. As a software engineer myself, I like to approach testing optimization models using testings methods used for traditional software engineering.

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


### Helpful links

It's hard to find good content on MIPs in general but I think the following links are extremely valuable:

https://www.youtube.com/watch?v=i1wg23MFA5I&list=PLaoe2MTbJBvpFPyMMSOB-WrHofdHo3e74&ab_channel=MikeWagner (best introduction to LP and MIP for a software engineer that I could find)

https://netflixtechblog.com/predictive-cpu-isolation-of-containers-at-netflix-91f014d856c7

https://www.nextmv.io/blog/the-road-to-production-is-paved-with-testing-and-experimentation

https://www.nextmv.io/blog/testing-testing-1-2-3