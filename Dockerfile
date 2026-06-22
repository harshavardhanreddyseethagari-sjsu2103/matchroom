# Dockerfile
#
# This is a RECIPE, not a script you run with python3. Docker reads this
# file top to bottom and builds an "image" — a frozen, self-contained
# snapshot of an operating system + your code + your dependencies.
#
# Build it with:
#   docker build -t fire-risk-api .
#
# Run it with:
#   docker run -p 8000:8000 fire-risk-api


# ── Step 1: Start from a base image ───────────────────────────
# Instead of building an OS from scratch, we start from an existing
# image that already has Python 3.11 installed on a minimal Linux
# distro ("slim" = stripped down, smaller download, faster builds).
FROM python:3.11-slim

# ── Step 2: Set the working directory INSIDE the container ────
# Everything from here on happens inside this folder, INSIDE the
# container's tiny isolated filesystem — completely separate from
# your Mac's actual filesystem.
WORKDIR /app

# ── Step 3: Copy just the requirements file first ─────────────
# We copy ONLY requirements.txt before the rest of the code on purpose.
# Docker caches each step. If your code changes but requirements.txt
# doesn't, Docker reuses the cached "pip install" step instead of
# re-downloading every package on every build. This ordering is a
# standard Docker performance habit, not an accident.
COPY requirements.txt .

# ── Step 4: Install the dependencies INSIDE the image ─────────
# This runs pip install, but inside the container's Linux environment,
# not on your Mac. The packages get baked into the image itself.
RUN pip install --no-cache-dir -r requirements.txt

# ── Step 5: Copy the rest of your project files in ────────────
# The "." means "everything in the current folder on my Mac"
# (where the Dockerfile lives), copied to "." inside the container
# (which is /app, because of WORKDIR above).
COPY . .

# ── Step 6: Document which port the app listens on ────────────
# This doesn't actually open the port by itself — it's metadata/
# documentation for anyone reading this Dockerfile. The real port
# mapping happens in the `docker run -p` command.
EXPOSE 8000

# ── Step 7: The command that runs when the container STARTS ───
# This is what actually launches your API when someone runs the image.
# Note: 0.0.0.0 instead of 127.0.0.1 — this means "accept connections
# from outside the container," not just from inside it. If we used
# 127.0.0.1 here, the API would only talk to itself and you'd never
# be able to reach it from your Mac's browser.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]