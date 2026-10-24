# WSL side: when the internal CFD has finished, export its 3D field, then mark done
until grep -q INAIR_FINAL_DONE ~/cfd/inair3.log 2>/dev/null || ! tmux has-session -t inair3 2>/dev/null; do sleep 30; done
bash /mnt/c/Users/vibhe/Downloads/OUTPUT/CFD/scripts/export3d.sh fluid inair_continuous
touch ~/cfd/inair_export.done
