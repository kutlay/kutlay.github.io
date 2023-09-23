---
title: Running Stable Diffusion Models on CPU
layout: post
category: software
---

I recently got into deep learning and went over <a href="https://www.youtube.com/watch?v=QDX-1M5Nj7s&list=PLtBw6njQRU-rwp5__7C0oIVt26ZgjG9NI" target="_BLANK">MIT's 6.S191</a> to understand the fundamentals. I absolutely recommend at least doing their labs as they teach you the fundamentals pretty quickly and give you some hands-on experience.

After writing a couple of toy models, I found myself trying to generate funny images on publicly available Stable Diffusion models, which often make you wait for a long time and don’t give you a lot of options to customize your image. I don’t want to get into the whole business of buying a GPU or figuring out how to use the GPU on an AWS machine so I wanted to give a classic VM with a moderate CPU a try to generate images. In the end, I don’t need a fast model, I just need something I have full control over so I can generate images like this one:

| ![Astronout cat? sort of](assets/images/astronout-cat.png) |
|:--:| 
| *For reference, this takes ~15 seconds* |

Thankfully the community has already done most of the work for me. There are already tools to easily load models and run prompts such as <a href="https://github.com/AUTOMATIC1111/stable-diffusion-webui">stable-diffusion-webui</a> and HuggingFace has an amazing community with thousands of models available to use.

All I had to do was to install these tools and make sure they were working. The only problem is that the hardware dependency is more of a problem when it comes to models like these so it takes a bit of a trial and error to get things running. I needed to play with different flags to disable using the GPU and enable special modes that don't run certain tests to make it work on a CPU.

(If you're very excited to generate your "cat in space" image and don't want to deal with the details, you can simply use the <a href="https://cloud.linode.com/stackscripts/1241119">StackScript</a> I created which installs everything you need.)

---
{: data-content="Installation"}

(All instructions from now on are tested on an Ubuntu 22.04 Linode VM)

The below code block installs everything you need and starts the web UI at the end. `--share` tag will create a public URL, which will look like `Running on public URL: https://98..sdf.gradio.live`.

 
```bash
#!/bin/bash

# Install requirements for stable-diffusion-webui installation
sudo apt update
sudo apt install -y wget git python3 python3.10-venv libgl1 libglib2.0-0

mkdir webui
cd webui

python3 -m venv venv/

wget -q https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui/master/webui.sh

echo 'export COMMANDLINE_ARGS="--disable-nan-check --skip-torch-cuda-test --upcast-sampling --no-half-vae --no-half --use-cpu SD GFPGAN BSRGAN ESRGAN SCUNet CodeFormer --all"' >> webui-user.sh

bash webui.sh -f --share
```

If everything goes well, you should have the web UI ready! 

---
{: data-content="Models"}

At the time of this writing, the web UI comes with a model <a href="https://huggingface.co/runwayml/stable-diffusion-v1-5">v1-5-pruned-emaonly.safetensors</a>. This is a cutting-edge model traiend on 512x512 images. 

Things move very fast in the stable diffusion world so you will find much better models on HuggingFace. You can use <a href="https://huggingface.co/models?pipeline_tag=text-to-image&sort=trending">this link</a> to look at the most popular ones. All you need to do is to pick one of them, go to the "Files and Version" tab on the model's HuggingFace page, and find the `.safetensors` file. Download that file to `stable-diffusion-webui/models/` and web UI will pick it up automatically.

Here are a few things to pay attention to while you're trying a new model:

- Make sure to understand what they're trained on. For example, if the model is trained on 512x512 images, you will have much better results generating 512x512.
- The bigger the model, the slower the inference, and especially since we're trying to use CPU, it's more painful. 

---
{: data-content="Samplers"}

Sampling method is one of the most important variables while generating an image. For starters, you can go with DPM2 Karras or Euler. <a href="https://stable-diffusion-art.com/samplers/">Here</a> is a good blog post explaining difference between all samplers.