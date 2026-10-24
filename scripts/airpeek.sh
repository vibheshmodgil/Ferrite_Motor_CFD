cd ~/cfd/air; grep -E "^Time =" log.run | tail -1; grep "continuity" log.run | tail -2; grep "Solving for p_rgh" log.run | tail -2 | cut -c1-110; grep -E "FATAL|exception" log.run | head -3
