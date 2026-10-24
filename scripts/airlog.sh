sed -n '/^Time = 1s/,/^Time = 3s/p' ~/cfd/air/log.run | cut -c1-120 | head -40
