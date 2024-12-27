# Social Media Posts Scheduler

A simple social media posts scheduler. Built with Django and AlpineJs.
Checkout [postiz.com](https://postiz.com/) it's also open-source!


## Get social media OAuth2 ids and secrets

For all of them you need to search for developer + X or developer + Linkedin etc. to go to the platform where you can create an app and get the keys needed for integrating with their api. Search for "How to make posts via Linkedin/X/Facebook/etc api" you will find some up to date docs on what steps you need to take. Check .env.example for the needed ids and secrets.


## Quickstart

Install dependencies:
- `virtualenv .venv`;
- `source .venv/bin/activate`;
- `pip install -r requirements.txt`;

Run migrations:
- `make migrate-all`;

Run the application:
- `make web` - start web app (open browser at `http://localhost:8000/`);
- `make cron` - start post scheduler;


## Usage

Go to integrations and authorize app to post. Use ngrok during development (add redirect oauth2 urls on developer portals).

![integrations](pics/integrations.png)

Plan content up to 3 years ahead. 

![calendar](pics/calendar.png)

Add post text and media file (image), set time on which this post should be published. 
Click `Next` to go to the next day and post.

![posts](pics/posts.jpeg)

Externalize writing posts via an excel file which you can import. Delete all posts or old posts to free up disk space.

![bulk](pics/bulk.png)

## Observations

Currently you can post on: Linkedin, X, Threads, Facebook (public page) (Not ready: Instagram, Tiktok, Youtube).
You can post text with an optional image. The app is open to PRs (see issues) but not actively maintained.
