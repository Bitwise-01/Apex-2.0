# ApeX

Apex, a tool that uses social engineering to get WIFI keys.

### Requirements

- Kali Linux
- Python V3.9

### Installation

```sh
chmod +x setup.sh
./install.sh
```

1. Install pipenv

```
pip install pipenv
```

2. Create virtual environment

```
pipenv install
```

### Usage

```sh
pipenv run python server.py
```

### Dashboard

The link to the dashboard can be found in the out of the `server.py` file<br>
it will look similar to `http://localhost/3ebb0288-b156f6c5d352a8da-0d908d0d`.<br>
The link changes each time you run the `server.py`; this is to make it difficult<br>
for unwanted users from accessing the dashboard.
