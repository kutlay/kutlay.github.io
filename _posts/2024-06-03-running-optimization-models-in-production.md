---
title: Running Optimization Models in Production 
layout: post
category: software
---

I've been working on an optimization model at Akamai for about 2 years now. It is a fairly complicated model we use for CDN capacity planning and it certainly needs a lot of care to keep it running at a weekly cadence. Most of the issues we've had is regarding the quality of the input data, just like any other data heavy project.

We've been lucky to have the luxury of owning our own interface to show the results of the optimization model, so we pretty much control the whole life cycle of collecting data from various parts of the company and presenting it to the internal users. We set the frequency of the model runs (a week for now) and when something goes bad we have enough time to fix it and re-run it before the next run. This gives us a much higher tolerance for run failures. This fortunate situation allowed us to not invent in crazy amount of tests and "production level" consistency (which I'm still not 100% what that means).

Recently I joined a new project to develop an optimization model for Linode's VM allocation problem. Even though the nature of the problem is very similar (essentially bin packing with lots of constraints) the cadence and the positioning of the model runs are much different. This time, the requirements are:

- Highly available API which runs the same underlying model on-demand with different sets of inputs for each endpoints
- Scheduled (pretty frequently, like every hour) runs where the results are published for other system's use
- Ability to make changes to the underlying model in much higher cadence since the company is just started to focus on the problem

In this post I'm going to explore what is needed to achieve these goals.

## Backend Service Design

The only unique part of this service is that the main process (running the optimization model) takes a long time. 

## Testing

### Unit Tests

### Functional Tests

### Stress Tests
