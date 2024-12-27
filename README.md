# Social Media Posts Scheduler

A simple social media posts scheduler. Built with Django and AlpineJs.


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

Why I Stopped Working on This App:

1. All platforms have their own post schedulers (a bit rudimentary for some, but they work). It's a minor inconvenience to copy and paste content on all platforms and schedule it (this app is a "vitamin" not a "painkiller").

2. Posting the same content on all platforms doesn't yield expected results. Each platform has its own users and their expectations. On TikTok, you expect one type of content; on LinkedIn, another.

3. APIs need to be maintained. After dealing with the Facebook API, I got tired of it (I mistakenly deleted the main account linked to a business portfolio and can't reverse that).

4. Videos are large and require AWS S3. I wanted to sell this as a one-time service setup for small businesses with the offer of "Cheap online presence on all platforms for $5 per month." It can be cheap if posts are deleted from the VPS/S3 after they are published, but I can't guarantee $5 per month anymore. Maybe this app should be moved to Firebase?