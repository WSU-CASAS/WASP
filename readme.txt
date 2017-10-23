WASP (WSU Algorithmic Sensor Placement)

Author: Brian Thomas


This is assuming you have set up the postgresql server with the sql schema I 
provided (and updated the connection string WASP_Manager.py:88 if not using a 
localhost connection, and GA_Reproduce:224), and set up an ejabberd server 
with the following usernames registered (replace "hostname" with the hostname 
you registered the accounts with):

boss@hostname
manager0@hostname
manager1@hostname
manager2@hostname
worker0@hostname
worker1@hostname
worker2@hostname


NOTE:
    You can run just 1 worker, or 20, they will be doing the cpu intensive
    work for the boss.  Here I present running 3 managers at once, but you can
    just run 1 at a time (1 manager is 1 run of the GA, each manager listed
    here has a slightly different configuration).  Feel free to modify the
    launchManagers.py or look at it for ways to launch multiple managers that
    cover all possible combinations of the provided search spaces.  All of the
    scripts here will output the command line args if you type:
            ./script.py --help

Now for starting up the system:

# open new terminal window/tab
cd wasp-FINAL
mkdir -p tmp/boss_working_directory
python2 WASP_Boss.py --jid=boss@hostname
                     --password=bosspassword
                     --workingDir=tmp/boss_working_directory

# open new terminal window/tab
cd wasp-FINAL
mkdir -p tmp/worker0
cp ar tmp/worker0/.
python2 WASP_Worker.py --jid=worker0@hostname
                       --password=worker0password
                       --dir=tmp/worker0
                       --boss=boss@hostname
                       --pypath=/usr/bin/python2

# open new terminal window/tab
cd wasp-FINAL
mkdir -p tmp/worker1
cp ar tmp/worker1/.
python2 WASP_Worker.py --jid=worker1@hostname
                       --password=worker1password
                       --dir=tmp/worker1
                       --boss=boss@hostname
                       --pypath=/usr/bin/python2

# open new terminal window/tab
cd wasp-FINAL
mkdir -p tmp/worker2
cp ar tmp/worker2/.
python2 WASP_Worker.py --jid=worker2@hostname
                       --password=worker2password
                       --dir=tmp/worker2
                       --boss=boss@hostname
                       --pypath=/usr/bin/python2

# open new terminal window/tab
cd wasp-FINAL
mkdir -p tmp/manager0
cp dna.db tmp/manager0/.
cp config/kyoto.xml tmp/manager0/site.xml
python2 WASP_Manager.py --jid=manager0@hostname
                        --password=manager0password
                        --dir=tmp/manager0
                        --data=data_run
                        --orig=data_orig
                        --boss=boss@hostname
                        --pypath=/usr/bin/python2
                        --population=50
                        --random=0.1234
                        --mutation_rate=0.005
                        --crossover=1
                        --survival_rate=0.10
                        --reproduction_rate=0.20
                        --seed_size=5
                        --size_limit=25
                        --max_generations=300

# open new terminal window/tab
cd wasp-FINAL
mkdir -p tmp/manager1
cp dna.db tmp/manager1/.
cp config/kyoto.xml tmp/manager1/site.xml
python2 WASP_Manager.py --jid=manager1@hostname
                        --password=manager1password
                        --dir=tmp/manager1
                        --data=data_run
                        --orig=data_orig
                        --boss=boss@hostname
                        --pypath=/usr/bin/python2
                        --population=50
                        --random=0.1234
                        --mutation_rate=0.001
                        --crossover=1
                        --survival_rate=0.10
                        --reproduction_rate=0.20
                        --seed_size=5
                        --size_limit=25
                        --max_generations=300

# open new terminal window/tab
cd wasp-FINAL
mkdir -p tmp/manager2
cp dna.db tmp/manager2/.
cp config/kyoto.xml tmp/manager2/site.xml
python2 WASP_Manager.py --jid=manager2@hostname
                        --password=manager2password
                        --dir=tmp/manager2
                        --data=data_run
                        --orig=data_orig
                        --boss=boss@hostname
                        --pypath=/usr/bin/python2
                        --population=50
                        --random=0.1234
                        --mutation_rate=0.005
                        --crossover=2
                        --survival_rate=0.10
                        --reproduction_rate=0.20
                        --seed_size=5
                        --size_limit=25
                        --max_generations=300

