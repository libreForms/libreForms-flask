![header img](header_img_large.png)

## libreForms
an open form manager API

## about
Liberate your forms with libreForms, an open form manager API that's intended to run in your organization's intranet. Most browser-based form managers lack key features, direct control over the underlying application, self-hosting support, a viable cost/licensing model, or lightweight footprints. The libreForms project, first and foremost, defines a simple but highly extensible abstraction layer that matches form fields to data structures. It adds a browser-based application, document-oriented database, and data visualizations and a RESTful API on top of this. 

![abstraction layer](libreForms_abstraction_layer.drawio.svg)

## use cases
- You are a small enterprise that has been using Google Forms for your organization's internal forms because it is low-cost, but you dislike the restricted features and lack of direct control over your data.

- You are a medium-sized enterprise that wants a simple, low-cost tool to manage their internal forms. You don't mind self-hosting the application, and you have staff with rudimentary experience using Python to deploy and maintain the system.

- You are a large enterprise with significant technical staff that routinely host and maintain applications for use on your organization's intranet. You have assessed options for form managers on the market and determined that proprietary services provide little direct control over the application source code, or otherwise fail to provide a viable licensing model.

## features
- a form-building abstraction layer based on Python dictionaries
- a flask web application (http://x.x.x.x:8000/) that will work well behind most standard reverse-proxies 
- plotly dashboards for data visualization
- a document-oriented database to store form data 
- \[future\] local and SAML authentication options
- \[future\] support for lookups in form fields & routing lists for form review, approvals, and notifications



```{toctree}
---
maxdepth: 2
numbered: 1
---
index.md
web-app.md
api.md
```