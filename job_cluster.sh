#!/bin/bash
#SBATCH --job-name=teste_hostname  #nome do JOB
#SBATCH -p general  #nome da particao
#SBATCH --ntasks=1   #nº de tarefas
#SBATCH --cpus-per-task 32 # nº de CPU/cores por tarefa
#SBATCH --mem=32G    # memória total
#SBATCH --output=output.txt   #arquivo saida
#SBATCH --error=error.err    #log de erro
#SBATCH --mail-user=denilsonfbar@gmail.com  #digite o seu email
#SBATCH --mail-type=BEGIN,END,FAIL

# Activate the virtual environment
source venv/bin/activate

# Execute the Python script for the experiment
python OrthoFinder_source/orthofinder.py -f data/proteomes -t 32 -S diamond

# Deactivate the environment (optional but good practice)
deactivate