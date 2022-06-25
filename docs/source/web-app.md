## Installation (RHEL 8)

0. install dependencies

```
# see https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-red-hat/
echo "[mongodb-org-5.0] 
name=MongoDB Repository 
baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/5.0/x86_64/ 
gpgcheck=1 
enabled=1 
gpgkey=https://www.mongodb.org/static/pgp/server-5.0.asc" | tee /etc/yum.repos.d/mongodb-org-5.0.repo
yum update -y
yum install python3.8 mongodb-org -y
systemctl enable --now mongodb
```

1. Download this repository into the opt directory:

**Method 1: `wget` stable release**

```
cd /opt
wget https://github.com/signebedi/libreForms/archive/refs/tags/X.X.X.tar.gz
tar -xvf libreforms-*.*.*.tar.gz
mv libreforms-*.*.* libreForms
```

**Method 2: `git clone` cutting edge repository**

```
cd /opt
git clone https://github.com/signebedi/libreForms.git
```

2. install Python virtual environment and initialize flask

```
cd /opt/libreForms
python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app
flask init-db
```

3. libreforms user

```
useradd --no-create-home --system libreforms
chown -R libreforms:libreforms /opt/libreForms
```

4. systemd service

```
cp /opt/libreForms/gunicorn/libreforms.service /etc/systemd/system
systemctl daemon-reload
systemctl enable --now libreforms
```

### Installation (Ubuntu 20.04)

0. install dependencies

```
apt update -y && apt upgrade -y
apt install -y mongodb python3-pip python3-venv # for the most up to date version of mongodb, see https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/
systemctl enable --now mongodb
```

1. Download this repository into the opt directory:

**Method 1: `wget` stable release**

```
cd /opt
wget https://github.com/signebedi/libreForms/archive/refs/tags/X.X.X.tar.gz
tar -xvf libreforms-*.*.*.tar.gz
mv libreforms-*.*.* libreForms
```

**Method 2: `git clone` cutting edge repository**

```
cd /opt
git clone https://github.com/signebedi/libreForms.git
```

2. install Python virtual environment and initialize flask

```
cd /opt/libreForms
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app
flask init-db
```

3. libreforms user

```
useradd --no-create-home --system libreforms
chown -R libreforms:libreforms /opt/libreForms
```

4. systemd service

```
cp /opt/libreForms/gunicorn/libreforms.service /etc/systemd/system
systemctl daemon-reload
systemctl enable --now libreforms
```

if you experience a failure when you check `systemctl status libreforms`, then try chowning the program files and restarting the application.

```
chown -R libreforms:libreforms /opt/libreForms
systemctl restart libreforms
```