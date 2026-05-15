# Deploying to Oracle Cloud Always Free

## 1. Create the VM

1. Open <https://cloud.oracle.com/> and sign in (sign up if needed — credit card required for verification, but Always Free resources won't be charged).
2. Compute → Instances → **Create Instance**.
3. Image: **Ubuntu 22.04**.
4. Shape: **Ampere A1 Flex** (ARM). 1 OCPU / 1 GB RAM is plenty.
5. Networking: keep default VCN; assign a public IPv4.
6. Add your SSH public key (`~/.ssh/id_rsa.pub`).
7. Click **Create**. Note the public IP once it boots.

> ⚠ Only use shapes marked **Always Free**. Anything else can incur charges.

## 2. SSH and prepare

```bash
ssh ubuntu@<PUBLIC_IP>
sudo apt update && sudo apt -y upgrade
sudo apt -y install python3.11 python3.11-venv git
```

## 3. Clone the project and configure

```bash
cd ~
git clone <YOUR_REPO_URL> Arsenal     # or scp the folder up if not using git
cd Arsenal
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env                              # paste in your tokens
```

## 4. Quick smoke test

```bash
source .venv/bin/activate
python -m src.main
```

Wait ~30 seconds — you should see logs from `match_watcher` and `news_poller`.
Press `Ctrl+C` to stop once you've confirmed it boots cleanly.

## 5. Install as a systemd service (24/7)

```bash
sudo cp deploy/arsenal-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now arsenal-bot
```

Verify:

```bash
systemctl status arsenal-bot
journalctl -fu arsenal-bot         # live log stream
```

## 6. Updating later

```bash
cd ~/Arsenal
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart arsenal-bot
```
