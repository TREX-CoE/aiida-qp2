
# AiiDA-qp2

## Installation

This is a brief installation guide fo aiida-qp2. First one needs to setup properly `aiida` it should be installed whten package is installed. Also RabbitMQ is importat to run `aiida`

```
# run it in sim kind of virtual environment

$ pip install aiida-qp2
```

### AiiDA profile

First we need to setup profile. One can use `postgreSQL` as a db backend but for simplicity we will show you SQLite setup:

```
$ verdi profile setup core.sqlite_dos
```

You will be promted some questions but answering them is easy

### AiiDA computer

Now you need to specify computer where you want to run your calculations. Here is the setup for your local computer. First setup a `yaml` file with setting called `localhost.yaml` and then setup the code.

```
$ cat localhost.yaml
---
label: "localhost"
hostname: "localhost"
transport: "core.local"
scheduler: "core.direct"
work_dir: "/var/tmp/aiida"
use_double_quotes: true
mpirun_command: "mpirun -np {tot_num_mpiprocs}"
mpiprocs_per_machine: "8"
prepend_text: " "
appent_test: " "

$ verdi copmuter setup --config localhost.yaml
```

### AiiDA code

Lastly we need to setup the code. Again to do the most simple setup one can pull docker image from docker hub.

```
$ docker push addman151/qp2-aiida:tagname
```

Unfortunatelly, the image is litle bit large, something what has to be fix in the future. When the image is downloaded we can continue by creating new code node inside AiiDA. Again we will use an yaml file.

```
$ cat qp.yaml
engine_command: "docker run -v $(pwd):/data {image_name}"
wrap_cmdline_params: false
use_double_quotes: false
image_name: 'qp2-aiida'
label: 'qp2-docker'
description: 'quantum package 2'
default_calc_job_plugin: 
  - 'qp2.create'
  - 'qp2.run'
filepath_executable: '/bin/entrypoint.sh'
computer: 'localhost'
prepend_text: ' '
append_text: ' '

$ verdi code create core.code.containerized --config qp.yaml
```

Now run `verdi status` and you should not see any error messages:
```
 ✔ version:     AiiDA v2.5.1
 ✔ config:      /home/.../.aiida
 ✔ profile:     profile
 ✔ storage:     SqliteDosStorage[...]: open,
 ✔ rabbitmq:    Connected to RabbitMQ v3.8.9 as amqp://guest:guest@...
```

## Running AiiDA qp2

```
echo "2

H 0.0 0.0 0.0
H 0.7 0.0 0.0" > H2.xyz

verdi data qp2.cli create --code qp2-docker@localhost --structure H2.xyz

verdi data qp2.cli list # Find pk of your project

verdi data qp2.cli activate <pk> # preplace by pk

verdi data qp2.cli run scf # Finally running HF calculation

verdi data qp2.cli show # Look at the results

```

I wrote these command from head hopefully there are no mistakes.

## Runnin QMC=Chem

Pull `QMC=Chem` docker image

```
docker pull addman151/qmcchem-aiida
```

You can install this code in the same way how the qp code was installed. In fact this image contain also `qp` so you can you this image also for previous calculations.

Recomended workflow follows:

```
verdi data qp2.cli run save_for_qmcchem --trexio-bug-fix
```

The option `--trexio-bug-fix` is there because there is a bug where one has to manually put absolute path to the trexio file. This flag will fix it.

Now run `QMC=Chem`:

```
verdi data qp2.cli run qmcchem -p "-t 1800" -p "-l 20"
```
