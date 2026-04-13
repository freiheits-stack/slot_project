Slot Project – Pseudo vs Quantum RNG Comparison

This project implements a configurable slot machine engine to compare
pseudo-random number generation and quantum random number generation
within a controlled experimental framework.

For generating the random numbers it supports:
- Live TrueRNG hardware
- Offline quantum bit sequences 
    -> txt-file, 
    -> every row is one bit sequence, typically one bit sequence for 1 complete game
        -> 32 bits per random number, 9-10 random numbers needed per Spin (depends if gamble mode is used)
- Pseudo Random Numbers

For Interactive live play (CLI mode):
type "python -m scripts.play_cli"
First choose you RNG source, for 1 (pseudo) you can set a seed to reproduce your game.
Set your start balance. 
Now you have the following options:
- spin   -> do 1 spin (default settings: bet 1, paylines 5, gamble_mode never, payout mode safe)
- auto N -> do N spins with actual settings
- set    -> change settings
            -> bet 1/3/5 (costs per spin)
            -> paylines 1/3/5 (1: middle line, 3: 3 horizontal lines, 5: additionally diagonal lines)
            -> gamble_mode always/never (double or nothing option in case of win)
            -> payout mode safe/risk (risk mode pays out less for middle high wins, but raises the higher wins)
- rng    -> change random source
- status -> display actual settings
- quit   -> end game

To check if the Live TrueRNG hardware mode is working properly, you can run "python -m tests.test_random"

To generate offline quantum bit sequences from live TrueRNG hardware
type "python -m scripts.generate_true_sequences.py"
It will save the output under data/truerng_sequences.txt
You can adjust the amount of needed bit sequences and bits per sequence with the following parameters:
N_SEQUENCES, SPINS_TARGET, DRAWS_PER_SPIN, SAFETY

For reproducible experiment runs (CSV output for statistical analysis):
type "python -m tests.experiment_runner"
It will run a fixed number of runs and spins from data/truerng_sequences.txt and Pseudo Random Souce and for gamble mode always and never for comparison
Default values: runs 50, start_balance 1000, max_spins 7000, bet 1, paylines 5, pseudo seed_base 12345
Possible stop reasons for a run are bankrupt or max_spins reached
The output will be experiment_runs.csv and experiment_spins.csv with the following values:
experiment_runs.csv: rng_type,run_id,seq_index,seed,gamble_mode,payout_mode,start_balance,end_balance,stop_reason,max_spins,spins_played,bet_per_line,active_paylines,total_bet,total_base_win,total_final_win,rtp_base,rtp_final,hit_rate_base,hit_rate_final,gamble_count,gamble_win_rate,max_loss_streak,max_win_streak,hit_gap_mean,hit_gap_var
experiment_spins.csv: rng_type,run_id,seq_index,seed,gamble_mode,payout_mode,spin_index,payout_base,payout_final,hit_base,hit_final,net_final,gamble_taken,gamble_win
The results of the analysis (done in Matlab) is saved under data/experiment_results.txt

