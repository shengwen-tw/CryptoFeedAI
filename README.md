# CryptoFeedAI

## Setup

1. Install Python packages and set timezone

```shell
sudo apt update
sudo apt install python3-venv -y
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo timedatectl set-timezone Asia/Taipei
```

2. Run `crontab -e`

```shell
0 9 * * * /home/shengwen1997_tw/CryptoFeedAI/run.sh
```
