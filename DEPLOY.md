# Deploy BrotHaus Bakery Simulator

This guide covers deploying the Flask app to free hosting platforms.

---

## Option 1: Render (Recommended – Free Tier)

1. **Push to GitHub** (if not already):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Go to [render.com](https://render.com) and sign up
   - Click **New → Web Service**
   - Connect your GitHub repo
   - Settings:
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn app:app`
     - **Instance Type:** Free
   - Click **Create Web Service**

3. Your app will be live at `https://your-app-name.onrender.com`

---

## Option 2: Railway

1. Go to [railway.app](https://railway.app) and sign up
2. Click **New Project → Deploy from GitHub**
3. Select your repo
4. Railway auto-detects the `Procfile` and deploys
5. Add a custom domain or use the generated `*.railway.app` URL

---

## Option 3: PythonAnywhere

1. Create a free account at [pythonanywhere.com](https://www.pythonanywhere.com)
2. Open **Web** tab → **Add a new web app**
3. Choose **Manual configuration** and Python 3.10+
4. In **Virtualenv**, create one and install:
   ```bash
   pip install -r requirements.txt
   ```
5. In **Code**, clone or upload your project
6. Set **WSGI configuration file** to point to your app:
   ```python
   import sys
   path = '/home/YOUR_USERNAME/YOUR_PROJECT'
   if path not in sys.path:
       sys.path.append(path)
   from app import app as application
   ```
7. Reload the web app

---

## Option 4: Fly.io

1. Install [flyctl](https://fly.io/docs/hands-on/install-flyctl/)
2. In your project folder:
   ```bash
   fly launch
   ```
3. Answer prompts (choose a region, don’t add a database)
4. Create `fly.toml` if needed, or use the generated one
5. Deploy:
   ```bash
   fly deploy
   ```

---

## Local Production Test

Before deploying, test with Gunicorn locally:

```bash
cd "/Users/preetishniket/Downloads/Assigment Model"
source venv/bin/activate
pip install gunicorn
gunicorn app:app
```

Then open http://127.0.0.1:8000 (Gunicorn uses port 8000 by default).
