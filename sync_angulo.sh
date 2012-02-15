#!/bin/bash

# Stop the demo
ssh fuchsia "cd ipol/; ./stop.sh";

# Synchronize all the needed stuff that is not in the app/ folder
rsync -avz *.py *.txt doc lib utils fuchsia:~/ipol/demo/

# Synchronize all the needed stuff in the app/d_angulo folder
rsync -avz app/d_angulo/*.py app/d_angulo/input app/d_angulo/template fuchsia:~/ipol/demo/app/d_angulo/ 
rsync -avz app/d_angulo/bin/*.sh fuchsia:~/ipol/demo/app/d_angulo/bin/

# Clean the dl/ and tmp/ folders
ssh fuchsia "cd ipol/demo/app/d_angulo/; rm -r tmp/*; dl/*" 

# Start the demo
ssh fuchsia "cd ipol/; ./start.sh"
