# 🚀 Deploy Your Workload Agent (Step-by-Step)

No coding experience needed. Follow each step in order.
Total time: about 20 minutes.

---

## Step 1 — Get a GitHub account (free)

1. Go to **github.com** → click **Sign up**
2. Create a free account

---

## Step 2 — Upload the code to GitHub

1. While logged into GitHub, click the **+** button (top right) → **New repository**
2. Name it `workload-agent`
3. Leave everything else as default → click **Create repository**
4. On the next page, click **uploading an existing file**
5. Drag and drop **all the files** from the `workload-agent-web` folder
   (select all files including the subfolders: `agent/`, `connectors/`, `storage/`, `static/`)
6. Click **Commit changes**

---

## Step 3 — Get a Railway account (free)

1. Go to **railway.app** → **Login with GitHub**
2. Authorize Railway to access your GitHub

---

## Step 4 — Deploy to Railway

1. In Railway dashboard, click **New Project**
2. Choose **Deploy from GitHub repo**
3. Select your `workload-agent` repository
4. Railway will detect it automatically — click **Deploy**
5. Wait about 2 minutes for the first build to finish

---

## Step 5 — Set your environment variables

This is how you securely give the app your passwords and API keys.
In Railway, click on your project → **Variables** tab → add each one below:

| Variable Name          | Value | Where to get it |
|------------------------|-------|-----------------|
| `API_KEY`              | Make up any password, e.g. `MyAgent2024!` | You decide this — it's how you log in |
| `ANTHROPIC_API_KEY`    | Your Anthropic key | console.anthropic.com → API Keys |
| `GMAIL_ADDRESS`        | your@gmail.com | Your Gmail address |
| `GMAIL_APP_PASSWORD`   | 16-character code | See below ↓ |
| `OUTLOOK_ADDRESS`      | your@outlook.com | Your Outlook address (optional) |
| `OUTLOOK_PASSWORD`     | Your password | Your Outlook password (optional) |
| `ASANA_ACCESS_TOKEN`   | Token from Asana | See below ↓ |
| `ASANA_WORKSPACE_GID`  | Your workspace ID | See below ↓ |

---

## Getting a Gmail App Password

This is a special one-time password for the app — it does NOT give full account access.

1. Go to **myaccount.google.com**
2. Click **Security** in the left menu
3. Under "How you sign in to Google", click **2-Step Verification** (turn it on if off)
4. Scroll down and find **App passwords** (search for it if you don't see it)
5. Under "App name" type `Workload Agent` → click **Create**
6. Copy the 16-character password shown → paste it into Railway as `GMAIL_APP_PASSWORD`

---

## Getting your Asana credentials

**Access token:**
1. Go to **app.asana.com** → click your profile picture → **My Profile Settings**
2. Click the **Apps** tab → **Manage Developer Apps** → **Personal access tokens**
3. Click **New access token** → name it `Workload Agent` → copy it

**Workspace GID:**
1. Go to **app.asana.com** in your browser
2. Look at the URL — it will contain a long number like `https://app.asana.com/0/1234567890/...`
3. That long number after `/0/` is your workspace GID

---

## Step 6 — Get your live URL

1. In Railway, click on your project → **Settings** tab → **Domains**
2. Click **Generate Domain** — you'll get a URL like `workload-agent.up.railway.app`
3. Open that URL in your browser
4. Log in with the `API_KEY` password you set in Step 5

---

## You're live! 🎉

Your dashboard will be at your Railway URL. Use it from any device.

**What to do first:**
1. Click **⚙️ Rules** → add a rule for your manager's email → HIGH priority
2. Click **🔄 Sync** — pulls the last 24 hours of email + all your Asana tasks
3. Click **📋 Summary** — Claude writes your morning briefing

---

## Keeping it running

- Railway's free tier gives you $5/month of compute, plenty for personal use
- Your tasks refresh every time you click Sync (or you can set up a daily auto-sync)
- To auto-sync every morning, go to Railway → your project → **Cron Jobs** → add:
  `0 8 * * *` with command `curl -X POST https://your-url/api/refresh -H "Authorization: Bearer YOUR_API_KEY"`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Invalid API key" at login | Check your `API_KEY` in Railway variables — no spaces |
| Gmail not syncing | Make sure App Password is correct and IMAP is on in Gmail settings |
| Outlook not syncing | Enable IMAP at outlook.com → Settings → Mail → Sync email |
| Asana not syncing | Double-check your access token and workspace GID |
| Build failed | Check Railway logs — usually a missing variable |
