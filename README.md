# Carbon Rewards Web Application

## Set up & Installation.

### 1 .Clone/Fork the git repo and create an environment 
                    
**Windows**
          
```bash
git clone https://github.com/SoumyashriSingha/Carbon-Rewards.git
cd Carbon-Rewards

```
### 2.create virtual environment
https://python.land/virtual-environments/virtualenv (Follow this link for creating virtual environment)

### 3. Then in terminal run:
```
pip install -r requirements.txt
```
### 4 .Migrate/Create a database

```python manage.py```

### 5. Run the application 

**On windows**
```
python routes.py
open localhost:5000
```
**For Raspberry pi**
```
Open terminal inside Carbon-Rewards-main

Run the following commands:
source venv/bin/activate
cd venv
sudo python3 routes1.py

Open localhost:5000
```



